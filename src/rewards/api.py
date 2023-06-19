from eth_keys import keys
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from web3 import Web3

from src.rewards.models import Peer
from src.rewards.schemas import PeerStatus

router = APIRouter(prefix="/api/v1")

invalid_input_response = JSONResponse(
    status_code=400,
    content={"error": "Invalid request: not a public key nor DUCX address"},
)


@router.post(
    "/status/{pubkey_or_address}",
    response_model=PeerStatus,
    description="get status of machine by public key or address",
)
async def get_enode_status(address_or_pubkey: str) -> JSONResponse:
    address_or_pubkey = address_or_pubkey.lower()
    if len(address_or_pubkey) == 128:
        try:
            pubkey_bytes = Web3.toBytes(hexstr=address_or_pubkey)
            keys.PublicKey(pubkey_bytes).to_checksum_address()
            query_arg = "enode"
        except Exception:
            return invalid_input_response
    else:
        try:
            address_or_pubkey = Web3.toChecksumAddress(address_or_pubkey)
            query_arg = "pubkey_address"
        except Exception:
            return invalid_input_response

    peer = await Peer.get_or_none(**{query_arg: address_or_pubkey})
    if not peer:
        return JSONResponse(
            status_code=401,
            content={"error": "This public key is not recognized by the backend"},
        )

    result = await peer.get_status()
    return JSONResponse(status_code=200, content=result)
