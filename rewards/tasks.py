import logging
from datetime import timedelta

from tortoise.transactions import atomic
from tortoise import timezone
from web3 import Web3
from eth_keys import keys

from rewards.models import Airdrop, AirdropStatus, Healthcheck, Peer, Rate, Reward
from rewards.settings import DECIMALS, config
from rewards.utils import request_active_enodes, count_reward_amount, pubkey_to_address

logger = logging.getLogger("tasks")


class AirdropException(Exception):
    pass


async def ping_nodes() -> None:
    active_enodes = await request_active_enodes()

    logger.debug("active nodes: \n{}".format("\n".join(active_enodes)))

    for enode in config.enodes:
        peer, _ = await Peer.get_or_create(
            enode=enode,
            defaults={
                "reward_interest": round(config.default_usd_reward_amount / 100, 18)
            },
        )

        is_online = enode in active_enodes
        timestamp = timezone.now() - timedelta(days=1)
        healthcheck_count = await Healthcheck.filter(
            peer=peer, timestamp__gte=timestamp
        ).count()
        if healthcheck_count:
            healthcheck = (
                await Healthcheck.filter(peer=peer).order_by("-timestamp").first()
            )
        else:
            healthcheck = await Healthcheck.create(peer=peer)
        if is_online:
            healthcheck.online_counter += 1
            logger.info(f"{enode} is online")
        healthcheck.total_counter += 1
        await healthcheck.save()

    session.close()


async def send_rewards() -> None:
    try:
        airdrop = await create_airdrop()
    except AirdropException:
        return

    await airdrop.relay()


@atomic()
async def create_airdrop() -> Airdrop:
    airdrop = await Airdrop.create()
    reward_count = 0
    for enode in config.enodes:
        peer, _ = await Peer.get_or_create(
            enode=enode,
            defaults={
                "reward_interest": round(config.default_usd_reward_amount / 100, 18)
            },
        )

        healthcheck = (
            await peer.healthchecks.filter(total_counter__gte=10)
            .order_by("-timestamp")
            .first()
        )
        online_percent = int(
            healthcheck.online_counter * 100 / healthcheck.total_counter
        )
        logger.info(f"{peer.enode} online percent is {online_percent}%")

        if online_percent >= config.reward_min_percent:
            address_checksum = pubkey_to_address(enode)
            amount = await count_reward_amount(float(peer.reward_interest), online_percent)
            await Reward.create(
                airdrop=airdrop,
                address=address_checksum,
                amount=amount,
            )
            reward_count += 1

    if not reward_count:
        raise AirdropException("Nothing to airdrop")
    logger.info("Airdrop created")
    return airdrop


@atomic()
async def check_pending_airdrops():
    airdrops = await Airdrop.filter(status=AirdropStatus.PENDING).select_for_update()
    logger.info(f"{len(airdrops)} pending airdrops")

    for airdrop in airdrops:
        await airdrop.check_relayed_tx()


@atomic()
async def check_waiting_airdrops():
    airdrops = await Airdrop.filter(
        status__in=(AirdropStatus.WAITING_FOR_RELAY, AirdropStatus.INSUFFICIENT_BALANCE)
    ).select_for_update()

    logger.info(f"{len(airdrops)} waiting airdrops")

    if airdrops:
        await airdrops[0].relay()


async def get_rate(currency: str) -> int:
    """
    Get rate for reward currency from API or from DB
    :param currency: reward currency
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
    rate = await Rate.get(currency=currency)
    return int(10**rate.decimals / rate.usd_rate)
