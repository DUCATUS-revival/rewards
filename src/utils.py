from typing import Set

import requests
from eth_keys import keys
from requests.adapters import HTTPAdapter
from web3 import Web3

from src.settings import config


async def request_active_enodes() -> Set[str]:
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

    session.close()
    return active_enodes


def pubkey_to_address(pubkey: str) -> str:
    pub_key_bytes = Web3.toBytes(hexstr=pubkey)
    pub_key = keys.PublicKey(pub_key_bytes)
    return pub_key.to_checksum_address()
