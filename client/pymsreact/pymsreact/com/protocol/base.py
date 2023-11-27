from enum import IntEnum
import logging

class ProtocolErrors(IntEnum):
    NO_ERROR                = 0
    TRANSPORT_ERROR         = 1
    MESSAGE_PARSING_ERROR   = 2
    MESSAGE_PACKING_ERROR   = 3

class BaseProtocol:
    """
    Abstract class for protocols

    ...

    Attributes
    ----------
    PROTOCOL_VERSION : string
        Contains the version of the protocol in "vX.Y" format
    MessageIDs : IntEnum
        Enumerates the implemented messages in this version of the protocol. 
        IMPORTANT: The GET_VERSION command always has to be implemented
    transport_layer : BaseTransport
       BaseTransport type to use for communication with the server
        
    Methods
    -------
    send_command(message)
        Sends messages over the WebSocket protocol
    receive_command()
        Waits for a command to be received
    """
    
    PROTOCOL_VERSION = 'v0.0'
    
    class MessageIDs(IntEnum):
        GET_VERSION             = 1
    
    def __init__(self, transport_layer):
        self.tl = transport_layer
        
    async def connect(self, address = None):
        pass
    async def disconnect(self):
        pass
    async def send_message(self, msg, payload = None):
        pass
    
    async def receive_message(self):
        msg = None
        payload = None     
        return (msg, payload)
        
class ProtocolException(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors
        self.logger = logging.getLogger("ProtocolException")
        self.logger.error(f'ProtocolException, error code: {self.errors} ' +
                          f'error name: {ProtocolErrors(self.errors).name}')