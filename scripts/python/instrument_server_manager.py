import asyncio
import logging
import multiprocessing
from enum import Enum
from multiprocessing import Queue
from protocol import Protocol
from queue import Empty, Full

class InstrumentServerManager:
    '''
    Parameters
    ----------
    
    '''
    
    class CallbackIds(Enum):
        SCAN = 1
        FINISHED_ACQUISITION = 2
        ERROR = 3
    
    def __init__(self, protocol, app_cb, loop):
        self.proto = protocol
        self.address = None
        self.acq_running = False
        self.acq_lock = asyncio.Lock()
        self.resp_cond = asyncio.Condition()
        self.resp = None
        self.logger = logging.getLogger(__name__)
        self.app_cb = app_cb
        
        self.msg_req_queue = multiprocessing.Manager().Queue()
        self.loop = loop
        
    async def connect_to_server(self, address = None):
        success = False
        
        if address is not None:
            self.address = address
            success = await self.proto.tl.connect(self.address)
        else:
            success = await self.proto.tl.connect()
        
        return success
        
    async def disconnect_from_server():
        self.address = None
        await self.proto.tl.disconnect()
        
    def get_protocol_version(self):
        self.logger.info('Getting protocol version')
        self.msg_req_queue.put((self.proto.MessageIDs.GET_SERVER_PROTO_VER_CMD,
                                self.proto.MessageIDs.SERVER_PROTO_VER_RSP))
        #await self.proto.send_message(self.proto.MessageIDs.GET_SERVER_PROTO_VER_CMD)
        #msg, payload = await self.wait_for_response()
        #if (self.proto.MessageIDs.SERVER_PROTO_VER_RSP == msg):
        #    self.logger.info(f'Received version: {payload}')
        #else:
        #    pass
            # Raise exception
        #return payload
        
    async def get_possible_params(self):
        self.logger.info('Getting possible parameters for requesting scans...')
        await self.proto.send_message(self.proto.MessageIDs.GET_POSSIBLE_PARAMS_CMD)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.POSSIBLE_PARAMS_RSP != msg):
            # TODO - raise exception
            self.logger.error("Response was not POSSIBLE_PARAMS message.")
            quit()
        return payload
        
    async def select_instrument(self, instrument):
        self.logger.info('Selecting instrument.')
        await self.proto.send_message(self.proto.MessageIDs.SELECT_INSTR_CMD,
                                      instrument)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with instrument selection.")
            raise Exception("Problem with instrument selection.")
        
    async def request_scan(self, parameters):
        #self.logger.info(f'Requesting scans with the following parameters:\n{parameters}')
        await self.proto.send_message(self.proto.MessageIDs.REQ_CUSTOM_SCAN_CMD,
                                      parameters)
        #msg, payload = await self.proto.receive_message()
        #if (self.proto.MessageIDs.OK_RSP != msg):
        #    self.logger.error("Problem with custom scan request.")
        #    raise Exception("Problem with custom scan request.")
        
    async def subscribe_to_scans(self):
        self.logger.info('Subscribing for scans.')
        await self.proto.send_message(self.proto.MessageIDs.SUBSCRIBE_TO_SCANS_CMD)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with subscribing to scans.")
            raise Exception("Problem with subscribing to scans.")
    
    async def unsubscribe_from_scans(self):
        self.logger.info('Unsubscribing from scans.')
        await self.proto.send_message(self.proto.MessageIDs.UNSUBSCRIBE_FROM_SCANS_CMD)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with unsubscribing from scans.")
            raise Exception("Problem with unsubscribing from scans.")
        
    async def configure_acquisition(self, config):
        self.logger.info('Configure the acquisition')
        await self.proto.send_message(self.proto.MessageIDs.CONFIG_ACQ_CMD, config)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with configuring acquisition.")
            raise Exception("Problem with configuring acquisition.")
        
    async def start_acquisition(self):
        self.logger.info('Start transferring scans from the raw file by the mock')
        await self.proto.send_message(self.proto.MessageIDs.START_ACQ_CMD)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with starting acquisition.")
            raise Exception("Problem with starting acquisition.")
            
    async def stop_acquisition(self):
        self.logger.info('Stop transferring scans from the raw file by the mock')
        await self.proto.send_message(self.proto.MessageIDs.STOP_ACQ_CMD)
        msg, payload = await self.wait_for_response()
        if (self.proto.MessageIDs.OK_RSP != msg):
            self.logger.error("Problem with stopping acquisition.")
            raise Exception("Problem with stopping acquisition.")
        
    async def listen_for_messages(self):
        self.listening = True
        self.logger.info('Listening for messages started.')
        while self.listening:
            msg, payload = await self.proto.receive_message()
            await self.dispatch_message(msg, payload)
        self.logger.info('Exited listening for messages loop.')
    
    async def dispatch_message(self, msg, payload):
        msg_type = msg.name[-3:]
        if ('RSP' == msg_type):
            async with self.resp_cond:
                self.resp = (msg, payload)
                self.resp_cond.notify()
        elif ('EVT' == msg_type):
            if (self.proto.MessageIDs.FINISHED_ACQ_EVT == msg):
                self.logger.info('Finish message received in instrument server manager')
                self.app_cb(self.CallbackIds.FINISHED_ACQUISITION, None)
            elif (self.proto.MessageIDs.SCAN_EVT == msg):
                #self.logger.info('Scan received in instrument server manager')
                self.app_cb(self.CallbackIds.SCAN, payload)
        else:
            pass
            
            # That is an error situation
    
    async def submit_message(self, msg, expected_rsp):
        payload = None
        await self.proto.send_message(msg)
        if expected_rsp is not None:
            received_rsp, payload = await self.wait_for_response()
            if (received_rsp != expected_rsp):
                error_msg = (f'Problem with sending message: {msg.name}. ' +
                            f'Expected response: {excpected_rsp.name}, ' +
                            f'received response: {received_rsp.name}.')
                self.logger.error(error_msg)
                raise Exception(error_msg)
        return payload
            
    def acquisition_finished(self):
        # Do all actions related to acquisition finishing
        pass
        
    async def wait_for_response(self):
        async with self.resp_cond:
            await self.resp_cond.wait()
            received_resp, resp_payload = self.resp
            self.resp = None
        self.logger.info(f'Response: {received_resp.name}')
        return received_resp, resp_payload
   