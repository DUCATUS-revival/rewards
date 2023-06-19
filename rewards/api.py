from eth_account import Account
from web3 import Web3
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from rewards.models import Peer
from rewards.schemas import PeerStatus

router = APIRouter(
    prefix='/api/v1'
)

invalid_input_response = JSONResponse(
    status_code=400,
    content={"error": "Invalid request: not a public key nor DUCX address"}
)

@router.post(
    '/status/{pubkey_or_address',
    response_model=PeerStatus,
    description="get status of machine by public key or address"
)
async def get_enode_status(address_or_pubkey: str):
    address_or_pubkey = address_or_pubkey.lower()
    if len(address_or_pubkey) == 64:
        try:
            Account.from_key(address_or_pubkey)
            query_arg = "enode"
        except Exception as e:
            return invalid_input_response
    else:
        try:
            address_or_pubkey = Web3.toChecksumAddress(address_or_pubkey)
            query_arg = "address"
        except Exception as e:
            return invalid_input_response

    peer = await Peer.get_or_none(**{query_arg: address_or_pubkey})
    if not peer:
        return JSONResponse(
            status_code=401,
            content={"error": "This public key is not recognized by the backend"}
        )

    result = await peer.get_status()
    return JSONResponse(
        status_code=200,
        content=result
    )




