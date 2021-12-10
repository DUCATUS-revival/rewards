import os
import yaml
import json
import logging
from dataclasses import dataclass, field
from marshmallow_dataclass import class_schema
from web3 import Web3, HTTPProvider, contract
from eth_account import Account
from typing import Set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

logging.getLogger('apscheduler.executors.default').propagate = False


POSTGRES_URL = 'postgres://{user}:{password}@{hostname}:{port}/{db}'.format(
    user=os.getenv('POSTGRES_USER', 'rewards'),
    password=os.getenv('POSTGRES_PASSWORD', 'rewards'),
    hostname=os.getenv('POSTGRES_HOST', '127.0.0.1'),
    db=os.getenv('POSTGRES_DB', 'rewards'),
    port=os.getenv('POSTGRES_PORT', 5432),
)

MODELS_MODULE = "rewards.models"

TORTOISE_ORM = {
    "connections": {
        "default": POSTGRES_URL,
    },
    "apps": {
        "models": {
            "models": [MODELS_MODULE], 
            "default_connection": "default"
        },
    },
}

MULTISENDER_INITIAL_GAS = 100_000

MULTISENDER_GAS_ADDITION_PER_ADDRESS = 40_000


@dataclass
class Config:
    json_rpc: str
    enodes: Set[str]
    multisender_contract_address: str
    gas_price_gwei: int
    private_key: str
    reward_per_percent: float
    reward_min_percent: int
    rewards_hour: int
    w3: Web3 = field(init=False)
    multisender_contract: contract = field(init=False)
    address: str = field(init=False)

    def __post_init__(self):
        self.w3 = Web3(HTTPProvider(self.json_rpc))
        multisender_contract_address_checksum = Web3.toChecksumAddress(self.multisender_contract_address)
        self.multisender_contract = self.w3.eth.contract(address=multisender_contract_address_checksum, abi=MULTISENDER_ABI)
        self.address = Account.from_key(self.private_key).address
            

with open('rewards/multisender_abi.json') as f:
    MULTISENDER_ABI = json.load(f)


with open(os.path.dirname(__file__) + '/../config.yaml') as f:
    config_data = yaml.safe_load(f)
    
config: Config = class_schema(Config)().load(config_data)
