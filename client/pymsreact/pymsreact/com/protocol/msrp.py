import msgpack
from enum import IntEnum
from .base import BaseProtocol

class MSReactProtocol(BaseProtocol):
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
    transport_layer : BaseTransport
       BaseTransport type to use for communication with the server
        
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
        OK_RSP                      = 0
        ERROR_RSP                   = 1
        ERROR_EVT                   = 2
        GET_SERVER_SW_VER_CMD       = 3
        SERVER_SW_VER_RSP           = 4
        GET_SERVER_PROTO_VER_CMD    = 5
        SERVER_PROTO_VER_RSP        = 6
        GET_ACQ_RAW_FILE_NAME       = 7
        ACQ_RAW_FILE_NAME_RSP       = 8
        
        # Instrument message group
        GET_AVAILABLE_INSTR_CMD     = 20
        AVAILABLE_INSTR_RSP         = 21
        GET_INSTR_INFO_CMD          = 22
        INSTR_INFO_RSP              = 23
        GET_INSTR_STATE_CMD         = 24
        INSTR_STATE_RSP             = 25
        SELECT_INSTR_CMD            = 26
        DESELECT_INSTR_CMD          = 27

        # Acquisition message group
        CONFIG_ACQ_CMD              = 100
        START_ACQ_CMD               = 101
        STOP_ACQ_CMD                = 102
        FINISHED_ACQ_EVT            = 103
        SUBSCRIBE_TO_SCANS_CMD      = 104
        SCAN_EVT                    = 105
        UNSUBSCRIBE_FROM_SCANS_CMD  = 106
        GET_POSSIBLE_PARAMS_CMD     = 107
        POSSIBLE_PARAMS_RSP         = 108
        REQ_CUSTOM_SCAN_CMD         = 109
        CANCEL_CUSTOM_SCAN_CMD      = 110
        SET_REPEATING_SCAN_CMD      = 111
        CLEAR_REPEATING_SCAN_CMD    = 112
        UPDATE_DEF_SCAN_PARAMS_CMD  = 113

        # Mock message group 
        SET_MS_SCAN_LVL_CMD         = 200
        SHUT_DOWN_MOCK_SERVER_CMD   = 201
    
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
            
        return (msg_id, payload)