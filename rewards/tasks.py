import logging
from datetime import datetime, timedelta

import requests
from tortoise.transactions import atomic
from web3 import Web3

from rewards.models import Airdrop, AirdropStatus, Healthcheck, Peer, Reward
from rewards.settings import config


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

    result = requests.post(config.json_rpc, json=payload, headers=headers, timeout=30)

    peers = result.json()["result"]["peers"]
    active_enodes = set()
    for peer in peers:
        if peer["protocols"]["eth"]:
            active_enodes.add(peer["id"])

    logging.info("active nodes: {}".format("\n".join(active_enodes)))

    for enode in config.enodes:
        peer, _ = await Peer.get_or_create(enode=enode)

        is_online = enode in active_enodes
        if is_online:
            logging.info(f"{enode} is online")

        await Healthcheck.create(peer=peer, online=is_online)


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
        peer, _ = await Peer.get_or_create(enode=enode)

        healthchecks = peer.healthchecks.all()
        healthchecks_count = await healthchecks.count()
        if healthchecks_count == 0:
            continue

        apoch_start = datetime.now() - timedelta(days=1)

        success_checks = await peer.healthchecks.filter(
            online=True,
            timestamp__gte=apoch_start,
        ).count()
        online_percent = int(success_checks * 100 / healthchecks_count)
        logging.info(f"{peer.enode} online percent is {online_percent}%")

        if online_percent >= config.reward_min_percent:
            public_key_hash = Web3.sha3(hexstr=enode)
            address = Web3.toHex(public_key_hash[-20:])
            address_checksum = Web3.toChecksumAddress(address)
            await Reward.create(
                airdrop=airdrop,
                address=address_checksum,
                amount=online_percent * config.reward_per_percent * (10 ** 18),
            )
            reward_count += 1

    if not reward_count:
        raise AirdropException("Nothing to airdrop")
    logging.info("Airdrop created")
    return airdrop


@atomic()
async def check_pending_airdrops():
    airdrops = await Airdrop.filter(status=AirdropStatus.PENDING).select_for_update()
    logging.info(f"{len(airdrops)} pending airdrops")

    for airdrop in airdrops:
        await airdrop.check_relayed_tx()


@atomic()
async def check_waiting_airdrops():
    airdrops = await Airdrop.filter(
        status__in=(AirdropStatus.WAITING_FOR_RELAY, AirdropStatus.INSUFFICIENT_BALANCE)
    ).select_for_update()

    logging.info(f"{len(airdrops)} waiting airdrops")

    if airdrops:
        await airdrops[0].relay()
