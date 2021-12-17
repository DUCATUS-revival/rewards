import argparse
from datetime import date, datetime
from eth_keys import keys
from hdwallet import BIP44HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet, CoinType
from web3 import Web3
from hdwallet.utils import generate_mnemonic



class DucatusXMainnet(EthereumMainnet):
    COIN_TYPE = CoinType({
        "INDEX": 1060,
        "HARDENED": True
    })


parser = argparse.ArgumentParser()
parser.add_argument('n', metavar='N', type=int, help='priv keys number')

args = parser.parse_args()
priv_keys = []
pub_keys = []
date = datetime.now().strftime("%Y-%m-%d-%H.%M.%S")
for i in range(args.n):
    mnemonic = generate_mnemonic(language="english", strength=128)
    bip44_hdwallet = BIP44HDWallet(cryptocurrency=DucatusXMainnet, account=0, change=False, address=0)
    bip44_hdwallet = bip44_hdwallet.from_mnemonic(mnemonic=mnemonic)
    priv_key_hexstr = bip44_hdwallet.private_key()
    priv_key = keys.PrivateKey(
       Web3.toBytes(hexstr=priv_key_hexstr)
    )
    pub_key = str(priv_key.public_key)
    
    with open(f'privkeys-{date}.txt', 'a') as f:
        f.write(priv_key_hexstr[2:] + '\n')

    with open(f'mnemonics-{date}.txt', 'a') as f:
        f.write(mnemonic + '\n')

    with open(f'pubkeys-{date}.txt', 'a') as f:
        f.write(pub_key[2:] + '\n')

    with open(f'keys-{date}.csv', 'a') as f:
        to_write = ','.join([mnemonic, priv_key_hexstr[2:], pub_key[2:]])
        f.write(to_write + '\n')
