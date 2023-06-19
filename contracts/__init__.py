import json

with open("contracts/multisender_abi.json") as f:
    MULTISENDER_ABI = json.load(f)