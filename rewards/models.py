import logging
from enum import Enum
from eth_keys import keys

from tortoise import fields
from tortoise.models import Model
from tortoise.transactions import atomic
from web3 import Web3
from web3.exceptions import TransactionNotFound

from rewards.settings import (
    MULTISENDER_GAS_ADDITION_PER_ADDRESS,
    MULTISENDER_INITIAL_GAS,
    config,
    DECIMALS
)
from rewards.utils import request_active_enodes, pubkey_to_address

logger = logging.getLogger("models")


class AirdropStatus(str, Enum):
    WAITING_FOR_RELAY = "WAITING_FOR_RELAY"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    REVERT = "REVERT"


class Lock(Model):
    pass


class Airdrop(Model):
    status = fields.CharEnumField(
        AirdropStatus, default=AirdropStatus.WAITING_FOR_RELAY
    )
    nonce = fields.BigIntField(null=True)
    gas_price = fields.DecimalField(max_digits=32, decimal_places=0, null=True)
    tx_hash = fields.CharField(max_length=100, default="")

    rewards = fields.ReverseRelation["Reward"]

    async def check_relayed_tx(self):
        logging.info("check status")
        if self.status != AirdropStatus.PENDING:
            raise ValueError(
                "Airdrop: Relayed tx check is only available for pending airdrops"
            )

        try:
            receipt = config.w3.eth.getTransactionReceipt(self.tx_hash)
        except TransactionNotFound:
            return

        try:
            if receipt["status"] == 1:
                self.status = AirdropStatus.SUCCESS
                await self.save()
            elif receipt["blockNumber"] is None:
                return
            else:
                self.status = AirdropStatus.REVERT
                await self.save()
        except KeyError:
            return

    @atomic()
    async def relay(self):
        logging.info("trying to relay")
        await Lock.filter(pk=1).only("id").select_for_update()

        pending_airdrops_count = (
            await Airdrop.filter(status=AirdropStatus.PENDING)
            .exclude(pk=self.pk)
            .count()
        )

        if pending_airdrops_count:
            logging.info("there are pending airdrops already")
            return

        rewards = await self.rewards
        addresses = [Web3.toChecksumAddress(reward.address) for reward in rewards]
        amounts = [int(reward.amount) for reward in rewards]

        total_amount = sum(amounts)
        gas_limit = (
            MULTISENDER_INITIAL_GAS
            + MULTISENDER_GAS_ADDITION_PER_ADDRESS * len(amounts)
        )

        gas_price = config.gas_price_wei

        if config.w3.eth.get_balance(config.address) < total_amount + (
            gas_limit * gas_price
        ):
            self.status = AirdropStatus.INSUFFICIENT_BALANCE
            await self.save()
            logging.info(f'balance {config.w3.eth.get_balance(config.address)}')
            logging.info(f'need to send {total_amount + (gas_limit * gas_price)}')
            logging.info('relay insuff balance')
            return

        nonce = config.w3.eth.getTransactionCount(config.address, "pending")
        tx_params = {
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": gas_limit,
            "value": total_amount,
        }
        logging.info(
            f"ready to send rewards addresses={addresses} amounts={amounts} with tx params {tx_params}"
        )
        func = config.multisender_contract.functions.multisendETH(addresses, amounts)
        initial_tx = func.buildTransaction(tx_params)
        signed_tx = config.w3.eth.account.sign_transaction(
            initial_tx, config.private_key
        ).rawTransaction
        tx_hash = config.w3.eth.sendRawTransaction(signed_tx).hex()

        logging.info(f"tx hash {tx_hash}")
        self.tx_hash = tx_hash
        self.nonce = nonce
        self.gas_price = gas_price
        self.status = AirdropStatus.PENDING
        await self.save()


class Reward(Model):
    airdrop = fields.ForeignKeyField("models.Airdrop", related_name="rewards")
    address = fields.CharField(max_length=100)
    amount = fields.DecimalField(max_digits=100, decimal_places=0)


class Peer(Model):
    enode = fields.CharField(pk=True, max_length=128)
    healthchecks = fields.ReverseRelation["Healthcheck"]
    reward_interest = fields.DecimalField(default=1, decimal_places=18, max_digits=255)
    pubkey_address = fields.CharField(max_length=128, null=True, default=None)

    @property
    def peer_address(self) -> str:
        return pubkey_to_address(self.enode)

    async def get_current_online_status(self):
        active_enodes = await request_active_enodes()
        if self.enode in active_enodes:
            return True

        return False

    async def get_latest_healthcheck(self):
        return await self.healthchecks.order_by("-timestamp").first()

    async def get_current_online_percent(self):
        latest_healthcheck = await self.get_latest_healthcheck()
        if not latest_healthcheck:
            return 0.0

        return round(latest_healthcheck.online_counter * 100 / latest_healthcheck.total_counter, 2)

    async def get_today_expected_rewards(self):
        current_online_percent = await self.get_current_online_percent()
        if current_online_percent < config.reward_min_percent:
            return 0.0

        return Rate.count_reward_amount(float(self.reward_interest), current_online_percent)

    async def get_status(self):
        return {
            "online_status": self.get_current_online_status(),
            "online_percent": self.get_current_online_percent(),
            "expected_rewards": self.get_today_expected_rewards(),
        }


class Healthcheck(Model):
    peer = fields.ForeignKeyField("models.Peer", related_name="healthchecks")
    timestamp = fields.DatetimeField(auto_now_add=True)
    online_counter = fields.IntField(default=0)
    total_counter = fields.IntField(default=0)


class Rate(Model):
    currency = fields.CharField(max_length=10)
    usd_rate = fields.DecimalField(decimal_places=8, max_digits=255, default=1)
    decimals = fields.IntField(default=0)

    @classmethod
    async def get_rate(cls, reward_currency: str):
        """
        Get rate for reward currency from API or from DB
        :param reward_currency: reward currency
        :return: amount for 1 US dollar in reward currency with decimals
        """
        try:
            rates = await config.api.rates
            for i_currency in rates:
                decimals = DECIMALS.get(i_currency, 0)
                rate, _ = await Rate.get_or_create(currency=i_currency, decimals=decimals)
                rate.usd_rate = rates.get(i_currency).get("USD")
                await rate.save()
        except Exception as err:
            logger.warning("Cant get rates from API cause {err}".format(err=err))
        rate = await Rate.get(currency=reward_currency)
        return int(10 ** rate.decimals / rate.usd_rate)

    @classmethod
    async def count_reward_amount(cls, reward_interest: float, percent: int) -> int:
        """
        Convert reward from US dollars to reward currency
        :param reward_interest: reward interest of peer
        :param percent: percent Peer was online for pass day
        :return: reward amount with decimals
        """
        rate = await cls.get_rate(config.reward_currency)
        amount = percent * reward_interest * rate
        return int(amount)
