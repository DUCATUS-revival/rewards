import logging
from tortoise.models import Model
from tortoise import fields
from enum import Enum
from rewards.settings import config, MULTISENDER_INITIAL_GAS, MULTISENDER_GAS_ADDITION_PER_ADDRESS
from web3 import Web3
from tortoise.transactions import atomic, in_transaction
from web3.exceptions import TransactionNotFound



class AirdropStatus(str, Enum):
    WAITING_FOR_RELAY = 'WAITING_FOR_RELAY'
    INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE'
    PENDING = 'PENDING'
    SUCCESS = 'SUCCESS'
    REVERT = 'REVERT'


class Lock(Model):
    pass


class Airdrop(Model):
    status = fields.CharEnumField(AirdropStatus, default=AirdropStatus.WAITING_FOR_RELAY)
    nonce = fields.IntField(null=True)
    gas_price = fields.DecimalField(max_digits=100, decimal_places=0, null=True)
    tx_hash = fields.CharField(max_length=100, default='')

    async def check_relayed_tx(self):
        logging.info('check status')
        if self.status != AirdropStatus.PENDING:
            raise ValueError('Airdrop: Relayed tx check is only available for pending airdrops')

        try:
            receipt = config.w3.eth.getTransactionReceipt(self.tx_hash)
        except TransactionNotFound:
            return

        try:
            if receipt['status'] == 1:
                self.status = AirdropStatus.SUCCESS
                await self.save()
            elif receipt['blockNumber'] is None:
                return
            else:
                self.status = AirdropStatus.REVERT
                await self.save()
        except KeyError:
            return

    @atomic()
    async def relay(self):
        logging.info('trying to relay')
        await Lock.filter(pk=1).only("id").select_for_update()

        pending_airdrops_count = await Airdrop.filter(
            status=AirdropStatus.PENDING
        ).exclude(pk=self.pk).count()

        if pending_airdrops_count:
            logging.info('there are pending airdrops already')
            return

        rewards = await self.rewards
        addresses = [Web3.toChecksumAddress(reward.address) for reward in rewards]
        amounts = [int(reward.amount) for reward in rewards]

        total_amount = sum(amounts)
        gas_limit = MULTISENDER_INITIAL_GAS + MULTISENDER_GAS_ADDITION_PER_ADDRESS * len(amounts)
        gas_price = config.gas_price_gwei * (10 ** 9)

        if config.w3.eth.get_balance(config.address) < total_amount + (gas_limit * gas_price):
            self.status = AirdropStatus.INSUFFICIENT_BALANCE
            await self.save()
            return

        nonce = config.w3.eth.getTransactionCount(config.address, 'pending')
        tx_params = {
            'nonce': nonce,
            'gasPrice': gas_price,
            'gas': gas_limit,
            'value': total_amount,
        }
        func = config.multisender_contract.functions.multisendETH(addresses, amounts)
        initial_tx = func.buildTransaction(tx_params)
        signed_tx = config.w3.eth.account.sign_transaction(initial_tx, config.private_key).rawTransaction
        tx_hash = config.w3.eth.sendRawTransaction(signed_tx).hex()

        logging.info(f'tx hash {tx_hash}')
        self.tx_hash = tx_hash
        self.nonce = nonce
        self.gas_price = gas_price
        self.status = AirdropStatus.PENDING
        await self.save()

        

class Reward(Model):
    airdrop = fields.ForeignKeyField('models.Airdrop', related_name='rewards')
    address = fields.CharField(max_length=100)
    amount = fields.DecimalField(max_digits=100, decimal_places=0)
    


class Peer(Model):
    enode = fields.CharField(pk=True, max_length=128)


class Healthcheck(Model):
    peer = fields.ForeignKeyField('models.Peer', related_name='healthchecks')
    online = fields.BooleanField()
    timestamp = fields.DatetimeField(auto_now_add=True)
