import glob
import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Set

import yaml
from eth_account import Account
from marshmallow_dataclass import class_schema
from web3 import HTTPProvider, Web3, contract

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

logging.getLogger("apscheduler.executors.default").propagate = False


POSTGRES_URL = "postgres://{user}:{password}@{hostname}:{port}/{db}".format(
    user=os.getenv("POSTGRES_USER", "rewards"),
    password=os.getenv("POSTGRES_PASSWORD", "rewards"),
    hostname=os.getenv("POSTGRES_HOST", "127.0.0.1"),
    db=os.getenv("POSTGRES_DB", "rewards"),
    port=os.getenv("POSTGRES_PORT", 5432),
)

MODELS_MODULE = "rewards.models"

TORTOISE_ORM = {
    "connections": {
        "default": POSTGRES_URL,
    },
    "apps": {
        "models": {"models": [MODELS_MODULE], "default_connection": "default"},
    },
}

MULTISENDER_INITIAL_GAS = 100_000

MULTISENDER_GAS_ADDITION_PER_ADDRESS = 40_000


@dataclass
class Config:
    json_rpc_urls: List[str]
    enodes: Set[str]
    multisender_contract_address: str
    gas_price_wei: int
    private_key: str
    reward_per_percent: float
    reward_min_percent: int
    ping_nodes_interval_munutes: int
    ping_nodes_max_retries: int
    ping_nodes_retries_timeout_secs: int
    rewards_hour: int
    enodes_dir: str
    enodes: Set[str] = field(init=False)
    w3: Web3 = field(init=False)
    multisender_contract: contract = field(init=False)
    address: str = field(init=False)

    def __post_init__(self):
        enodes_tmp = []
        for filename in glob.glob(os.path.join(self.enodes_dir, "*.txt")):
            enodes_tmp += [line.strip() for line in open(filename)]

        self.enodes = set(enodes_tmp)
        self.w3 = Web3(HTTPProvider(self.json_rpc_urls))
        multisender_contract_address_checksum = Web3.toChecksumAddress(
            self.multisender_contract_address
        )
        self.multisender_contract = self.w3.eth.contract(
            address=multisender_contract_address_checksum, abi=MULTISENDER_ABI
        )
        self.address = Account.from_key(self.private_key).address


with open("rewards/multisender_abi.json") as f:
    MULTISENDER_ABI = json.load(f)


with open(os.path.dirname(__file__) + "/../config.yaml") as f:
    config_data = yaml.safe_load(f)

config: Config = class_schema(Config)().load(config_data)
