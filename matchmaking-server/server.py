import os
import signal
import json

import accelbyte_py_sdk
from accelbyte_py_sdk.core import MyConfigRepository
from accelbyte_py_sdk.services.auth import login_client
from accelbyte_py_sdk.api.ams import fleet_claim_by_keys
from accelbyte_py_sdk.api.ams.models import ApiFleetClaimByKeysReq
import asyncio
from websockets.asyncio.server import serve, broadcast
import http

# these environment variables are required:
# AB_BASE_URL
# AB_NAMESPACE
# AB_CLIENT_ID
# AB_CLIENT_SECRET

# these environment variables are optional:
# CLAIM_KEYS (default: "default")
# REGIONS (default: "us-west-2, us-east-1")
# LOCAL_SERVER (set this to the IP:PORT of a local server to always return that server's IP:PORT to clients instead of claiming a server from AMS)
default_claim_keys = os.environ.get("CLAIM_KEYS", "default").split(",")
default_regions = os.environ.get("REGIONS", "us-west-2, us-east-1").split(",")
localServer = os.environ.get("LOCAL_SERVER")

CONNECTIONS = set()
stop = False


def sigterm_handler(sig, frame):
    global stop
    stop = True


async def register(websocket):
    print("New connection")
    CONNECTIONS.add(websocket)
    try:
        await websocket.send("Waiting for match...")
        await websocket.wait_closed()
    finally:
        CONNECTIONS.remove(websocket)


async def matchmaker():
    while not stop:
        match_size = 2
        while len(CONNECTIONS) >= match_size:
            print("Match found! Requesting server...")
            matched_clients = list(CONNECTIONS)[:match_size]
            match_message = json.dumps({"type": "OnMatchFound", "message": "Match found! Requesting server..."})
            broadcast(matched_clients, "Match found! Requesting server...")
            # normally, the ordered list of regions to try to get a server from would come from the game client's matchmaking request
            # and is based on client ping times to each region.  
            # For this example, we keep the matchmaking logic super simple and just use a default list of regions
            host_port = claim(default_claim_keys, default_regions)
            if not host_port:
                print("No server available. Waiting...")
                match_message = json.dumps({"type": "OnMatchError", "message": "No server available. Waiting..."})
                broadcast(matched_clients, match_message)
                break
            print("Server found! Connecting players...")
            match_message = json.dumps({"type": "OnServerClaimed", "message": host_port})
            broadcast(matched_clients, match_message)
            await asyncio.sleep(0.1)  # so the message gets sent before closing the connection
            for ws in matched_clients:
                await ws.close()

        await asyncio.sleep(2)


def claim(claim_keys, regions, session_id="none"):
    if localServer:
        return localServer
    
    body = ApiFleetClaimByKeysReq().with_claim_keys(claim_keys).with_regions(regions).with_session_id(session_id)
    result, err = fleet_claim_by_keys(body=body)
    print(result, err)
    if err:
        return

    host_port = result.ip + ":" + str(result.ports["default"])
    print(host_port)
    return host_port


async def main():
    signal.signal(signal.SIGTERM, sigterm_handler)
    accelbyte_py_sdk.initialize()

    if not localServer:
        _, error = login_client()
        if error:
            print(error)
            exit(1)

    port = os.environ.get("PORT", 8080)

    async with serve(
            register,
            "",
            port,
            process_request=health_check):
        await matchmaker()  # run forever

def health_check(connection, request):
    if request.path == "/healthz":
        return connection.respond(http.HTTPStatus.OK, "OK\n")
    if request.path == "/test-claim":
        result = claim(default_claim_keys, default_regions)
        if not result:
            return connection.respond(http.HTTPStatus.NOT_FOUND, "No servers available\n")
        return connection.respond(http.HTTPStatus.OK, "server available at: "+result+"\n")


if __name__ == "__main__":
    asyncio.run(main())
