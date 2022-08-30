import logging
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter
from tortoise.transactions import atomic
from tortoise import timezone
from web3 import Web3

from rewards.models import Airdrop, AirdropStatus, Healthcheck, Peer, Rate, Reward
from rewards.settings import DECIMALS, config

logger = logging.getLogger("tasks")


class AirdropException(Exception):
    pass


async def ping_nodes() -> None:
    payload = {
        "method": "parity_netPeers",
        "params": [],
        "id": 1,
        "jsonrpc": "2.0",
    }

    headers = {"Content-Type": "application/json"}
    adapter = HTTPAdapter(max_retries=config.ping_nodes_max_retries)
    active_enodes = set()
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    for json_rpc in config.json_rpc_urls:
        res = session.post(
            json_rpc,
            json=payload,
            headers=headers,
            timeout=config.ping_nodes_retries_timeout_secs,
        )
        peers = res.json()["result"]["peers"]
        for peer in peers:
            if peer["protocols"]["eth"]:
                active_enodes.add(peer["id"])

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
            hex_enode = Web3.toHex(text=enode)
            public_key_hash = Web3.sha3(hexstr=hex_enode)
            address = Web3.toHex(public_key_hash[-20:])
            address_checksum = Web3.toChecksumAddress(address)
            amount = await count_reward_amount(peer, online_percent)
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


async def count_reward_amount(peer: Peer, percent: int) -> int:
    """
    Convert reward from US dollars to reward currency
    :param peer: rewarded peer
    :param percent: percent Peer was online for pass day
    :return: reward amount with decimals
    """
    interest = peer.reward_interest
    rate = await get_rate(config.reward_currency)
    amount = percent * interest * rate
    return int(amount)


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
