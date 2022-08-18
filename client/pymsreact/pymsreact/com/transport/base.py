from enum import IntEnum 

class TransportStates(IntEnum):
    DISCONNECTED    = 0
    CONNECTED       = 1
    RECEIVE         = 2
    SEND_MSG        = 3

class BaseTransport:
    """
    Abstract class for transport layers

    ...

    Attributes
    ----------
    address : str
            Address of the server to connect to. The format of the address 
            depends on the actual transport layer's implementation.
    """

    def __init__(self, address = None):
        """
        Parameters
        ----------
        address : str
            Address of the server to connect to. The format of the address 
            depends on the actual transport layer's implementation.
        """
        self.state = TransportStates.DISCONNECTED
        self.address = address
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    async def connect(self, address = None):
        """Connects to a server with the given address 
        ----------
        address : str
            Address of the server to connect to. The format of the address 
            depends on the actual transport layer's implementation.
        """
        pass
    async def disconnect(self):
        """Disconnects from a server"""
        pass
    async def send(self, msg):
        """Sends messages to the server
        Parameters
        ----------
        message : str
            Message to transport through the transport layer
        """
        pass
    async def receive(self):
        """Listens for messages from the connected server"""
        pass