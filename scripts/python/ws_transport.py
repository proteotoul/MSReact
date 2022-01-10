import asyncio
from transport_layer import TransportLayer
import websockets as ws
import ws_transport_exception as wste


class WebSocketTransport(TransportLayer):
    """
    A class creating a transport layer using WebSocket as transport for 
    communication

    ...

    Attributes
    ----------
    uri : str
       WebSocket uri (universal resource identifier) to connect to
        
    Methods
    -------
    connect_to_uri(uri)
        Connects to a uri using WebSocket protocol
    disconnect_from_uri()
        Disconnects from uri
    receive()
        Listens for messages over the WebSocket protocol
    send(message)
        Sends messages over the WebSocket protocol
    """

    def __init__(self, uri):
        """
        Parameters
        ----------
        uri : str
            WebSocket uri (universal resource identifier) to connect to
        """
        self.uri = uri
        self.ws_protocol = None
        self.state = self.TL_STATE_DISCONNECTED
        self.start_time = 0

    # __aenter__ is the asynchronous version of the __enter__ context manager
    async def __aenter__(self):
        await self.connect(self.uri)
        return self

    # __aexit__ is the asynchronous version of the __exit__ context manager
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self, uri):
        """Connects to a uri using WebSocket protocol
        Parameters
        ----------
        uri : str
            WebSocket uri (universal resource identifier) to connect to
        """
        if self.TL_STATE_DISCONNECTED == self.state:
            self.uri = uri
            self.ws_protocol = await ws.connect(uri=self.uri)
            self.state = self.TL_STATE_CONNECTED
        else:
            raise wste.WebSocketTransportException(
                    "Cannot connect to uri when already connected!", 
                    "Invalid WebSocketTransport State")

    async def disconnect(self):
        """Disconnects from a uri"""
        if self.state != self.TL_STATE_DISCONNECTED:
            await self.ws_protocol.close()
            self.state = self.TL_STATE_DISCONNECTED
        else:
            raise wste.WebSocketTransportException(
                "Cannot disconnect from uri when already disconnected!", 
                "Invalid WebSocketTransport State")

    async def receive(self):
        """Listens for messages over the WebSocket protocol"""
        if self.TL_STATE_CONNECTED == self.state:
            message = await self.ws_protocol.recv()
        else:
            raise wste.WebSocketTransportException(
                "Cannot listen on WebSocket when not connected!",
                "Invalid WebSocketTransport State")
        return message

    async def send(self, message):
        """Sends messages over the WebSocket protocol
        Parameters
        ----------
        message : str
            Message to transport through the WebSocket
        """
        if self.TL_STATE_CONNECTED == self.state:
            await self.ws_protocol.send(message)
        else:
            raise wste.WebSocketTransportException(
                "Cannot send on WebSocket when not connected!",
                "Invalid WebSocketTransport State")
                

async def main():
    uri = f'ws://localhost:4649/SWSS'
    eob = "END OF BROADCAST"
    async with WebSocketTransport(uri) as ws_transport:
        receiving = True
        while receiving:
            message = await ws_transport.receive()
            print(f'< {message} >')
            if message == eob:
                receiving = False


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
