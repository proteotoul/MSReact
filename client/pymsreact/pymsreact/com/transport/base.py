from enum import IntEnum 
import logging

class TransportStates(IntEnum):
    DISCONNECTED    = 0
    CONNECTED       = 1
    RECONNECTING    = 2
    RECEIVE         = 3
    SEND_MSG        = 4
    
class TransportErrors(IntEnum):
    NO_ERROR            = 0
    INVALID_STATE_ERROR = 1
    DISCONNECTION_ERROR = 2
    
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
        self.logger = logging.getLogger(__name__)
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
        
class TransportException(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors
        self.logger = logging.getLogger("TransportException")
        self.logger.error(f'TransportException, error code: {self.errors} ' +
                          f'error name: {TransportErrors(self.errors).name}')