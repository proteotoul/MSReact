import asyncio
import logging
import socket
from transport_layer import TransportLayer
import websockets as ws
import ws_transport_exception as wste


class WebSocketTransport(TransportLayer):
    """
    A class implementing a transport layer using WebSocket as transport for 
    communication

    ...

    Attributes
    ----------
    address : str
       IP address of the server to connect to eg. "172.18.160.1"
        
    Methods
    -------
    connect(address)
        Connects to a server with a given address using WebSocket protocol
    disconnect()
        Disconnects from the server
    receive()
        Listens for messages over WebSocket
    send(message)
        Sends messages over WebSocket
    """
    
    # Default port, service name and uri for websocket connections
    DEFAULT_PORT = '4649'
    DEFAULT_SERVICE = 'SWSS'
    DEFAULT_URI = f'ws://localhost:4649/DEFAULT'
    
    def __init__(self, address = None):
        """
        Parameters
        ----------
        address : str
            IP address of the server to connect to eg. "172.18.160.1"
        """
        
        # Get uri from address if address is provided. Declare ws_protocol, and
        # set state to disconnected.
        self.uri = self.__address_from_uri(address)
        self.ws_protocol = None
        self.state = self.TL_STATE_DISCONNECTED
        
        # Set the logging level to WARNING to avoid unnecessery logs coming out
        # from the websockets module
        websockets_logger = logging.getLogger('websockets')
        websockets_logger.setLevel(logging.WARNING)
        
        # Create module logger
        self.logger = logging.getLogger(__name__)

    # Should reconsider if there is a need for context managers if they are not
    # used.
    # __aenter__ is the asynchronous version of the __enter__ context manager
    async def __aenter__(self):
        # Revisit if not having maximum size can cause security issues
        await self.connect(self.uri, max_size = None)
        return self

    # __aexit__ is the asynchronous version of the __exit__ context manager
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        
    def __address_from_uri(self, address = None):
        """Converts the given address to a uri
        Parameters
        ----------
        address : str
            IP address of the server to connect to eg. "172.18.160.1"
        """
        if address is None:
            address = socket.gethostbyname(socket.gethostname())
        return f'ws://{address}:{self.DEFAULT_PORT}/{self.DEFAULT_SERVICE}'

    async def connect(self, address = None):
        """Connects to a server with the given address using WebSocket protocol
        Parameters
        ----------
        address : str
            IP address of the server to connect to eg. "172.18.160.1"
        """
        success = False
        
        if self.TL_STATE_DISCONNECTED == self.state:
            self.uri = self.__address_from_uri(address)
            self.logger.info(f'Uri: {self.uri}')
            try:
                # Revisit if not having maximum size can cause security issues
                self.ws_protocol = await ws.connect(uri=self.uri, 
                                                    max_size = None)
                self.state = self.TL_STATE_CONNECTED
                success = True
            except ConnectionRefusedError as crf:
                self.logger.error("The remote computer refused the network connection.")
        else:
            self.logger.error('Invalid WebSocketTransport State - ' +
                              f'Cannot connect to {address} when ' +
                              'already connected!')
                    
        return success

    async def disconnect(self):
        """Disconnects from a server"""
        if self.state != self.TL_STATE_DISCONNECTED:
            await self.ws_protocol.close()
            self.state = self.TL_STATE_DISCONNECTED
        else:
            raise wste.WebSocketTransportException(
                "Cannot disconnect from uri when already disconnected!", 
                "Invalid WebSocketTransport State")

    async def receive(self):
        """Listens for messages from the connected server over WebSocket"""
        message = ""
        
        if self.TL_STATE_CONNECTED == self.state:
                message = await self.ws_protocol.recv()
        else:
            raise wste.WebSocketTransportException(
                "Cannot listen on WebSocket when not connected!",
                "Invalid WebSocketTransport State")
        return message

    async def send(self, message):
        """Sends messages to the server over WebSocket
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
