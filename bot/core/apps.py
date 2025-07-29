import websockets
import json


from cryptography.hazmat.primitives.serialization import load_pem_private_key
from sqlalchemy.orm import scoped_session
from core.models import Event, Response
from websockets import ClientConnection
from base64 import b64encode
from pathlib import Path
from uuid import uuid4
from time import time
from os import getenv


class Bot():
    def __init__(self, scoped_session: scoped_session, symbol: str):
        self.scoped_session = scoped_session
        self.symbol = symbol

    async def run(self):
        async with websockets.connect('wss://ws-api.binance.com:443/ws-api/v3') as websocket:
            await self.authenticate(websocket)

            while True:
                response = await websocket.recv()

                data = json.loads(response)

                with self.scoped_session() as session:
                    if 'id' in data:
                        object = Response(
                            correlation_id=data.get('id'),
                            status=data.get('status'),
                            payload=response
                        )
                    else:
                        object = Event(
                            type=data.get('e'),
                            timestamp=data.get('E'),
                            payload=response
                        )

                    session.add(object)

                    session.commit()

                print(data)

    async def authenticate(self, websocket: ClientConnection):
        # https://developers.binance.com/docs/binance-spot-api-docs/websocket-api/request-security

        with open(Path(getenv('BINANCE_PRIVATE_KEY_PATH')), 'rb') as file:
            private_key = load_pem_private_key(file.read(), None)

        params = {
            'apiKey': getenv('BINANCE_API_KEY'),
            'timestamp': int(time() * 1000)
        }

        payload = '&'.join([f'{param}={value}' for param, value in sorted(params.items())])

        signature = b64encode(private_key.sign(payload.encode('ASCII')))

        params['signature'] = signature.decode('ASCII')

        await websocket.send(json.dumps({
            'id': str(uuid4()),
            'method': 'session.logon',
            'params': params
        }))

        await websocket.send(json.dumps({
            'id': str(uuid4()),
            'method': 'userDataStream.subscribe'
        }))
