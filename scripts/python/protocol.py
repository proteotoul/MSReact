import msgpack
import transport_layer
from enum import IntEnum
from protocol_layer import ProtocolLayer

class Protocol(ProtocolLayer):
    """
    A class providing protocol functionalities, including message protocol,
    serializing and deserializing messages.

    ...

    Attributes
    ----------
    PROTOCOL_VERSION : string
        Contains the version of the protocol in "vX.Y" format
    MessageIDs : IntEnum
        Enumerates the implemented messages in this version of the protocol. 
        IMPORTANT: The GET_VERSION message always has to be implemented
    transport_layer : TransportLayer
       TransportLayer type to use for communication with the server
        
    Methods
    -------
    send_message(message)
        Sends messages over the WebSocket protocol
    receive_message()
        Waits for a message to be received
    """
    PROTOCOL_VERSION = 'v0.1'
    
    class MessageIDs(IntEnum):
    
            # Communication message group
            GET_SERVER_SW_VER       = 1
            SERVER_SW_VER           = 2
            GET_SERVER_PROTO_VER    = 3
            SERVER_PROTO_VER        = 4
            ERROR                   = 5

            # Instrument message group
            GET_AVAILABLE_INSTR     = 20
            AVAILABLE_INSTR         = 21
            GET_INSTR_INFO          = 22
            INSTR_INFO              = 23
            GET_INSTR_STATE         = 24
            INSTR_STATE             = 25
            SELECT_INSTR            = 26
            DESELECT_INSTR          = 27

            # Acquisition message group
            START_ACQ               = 100
            STOP_ACQ                = 101
            FINISHED_ACQ            = 102
            SUBSCRIBE_TO_SCANS      = 103
            SCAN_TX                 = 104
            UNSUBSCRIBE_FROM_SCANS  = 105
            GET_POSSIBLE_PARAMS     = 106
            POSSIBLE_PARAMS         = 107
            REQ_CUSTOM_SCAN         = 108
            SET_REPEATING_SCAN      = 109
            CLEAR_REPEATING_SCAN    = 110

            # Mock message group 
            SET_MS_SCAN_LVL         = 200,
            SHUT_DOWN_MOCK_SERVER   = 201,
    
    def __init__(self, transport_layer):
        self.tl = transport_layer
        
    async def send_message(self, msg, payload = None):
        if (msg in self.MessageIDs):
            if (None == payload):
                await self.tl.send(msg.to_bytes(1, 'big'))
            else:
                msg = msg.to_bytes(1, 'big') + msgpack.packb(payload)
                await self.tl.send(msg)
        else:
            #TODO - Exception
            pass
    
    async def receive_message(self):
        msg = await self.tl.receive()
        # Parse messages
        msg_id = self.MessageIDs(msg[0])
        
        if (1 < len(msg)):
            payload = msgpack.unpackb(msg[1:])
        else:
            payload = None
            
        '''
        if ((self.MessageIDs.SCAN_TX == msg_id) or
            (self.MessageIDs.POSSIBLE_PARAMS == msg_id)):
            payload = msgpack.unpackb(msg[1:])
            '''
        return (msg_id, payload)