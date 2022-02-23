import asyncio
import logging
from multiprocessing import Queue
from protocol import Protocol
from queue import Empty, Full

class InstrumentServerManager:
    '''
    Parameters
    ----------
    
    '''
    def __init__(self, protocol, algo_sync, acq_cont):
        self.proto = protocol
        self.algo_sync = algo_sync
        self.acq_cont = acq_cont
        self.address = None
        self.acq_running = False
        self.acq_lock = asyncio.Lock()
        self.resp_cond = asyncio.Condition()
        self.resp = None
        self.logger = logging.getLogger(__name__)
        
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
        
    async def get_protocol_version(self):
        self.logger.info('Getting protocol version')
        await self.proto.send_message(self.proto.MessageIDs.GET_SERVER_PROTO_VER)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.SERVER_PROTO_VER == msg):
            self.logger.info(f'Received version: {payload}')
        else:
            pass
            # Raise exception
        return payload
        
    async def get_possible_params(self):
        self.logger.info('Getting possible parameters for requesting scans...')
        await self.proto.send_message(self.proto.MessageIDs.GET_POSSIBLE_PARAMS)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.POSSIBLE_PARAMS != msg):
            # TODO - raise exception
            self.logger.error("Response was not POSSIBLE_PARAMS message.")
            quit()
        return payload
        
    async def select_instrument(self, instrument):
        self.logger.info('Selecting instrument.')
        await self.proto.send_message(self.proto.MessageIDs.SELECT_INSTR,
                                      instrument)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.OK != msg):
            self.logger.error("Problem with instrument selection.")
            raise Exception("Problem with instrument selection.")
        
    async def request_scan(self, parameters):
        #self.logger.info(f'Requesting scans with the following parameters:\n{parameters}')
        await self.proto.send_message(self.proto.MessageIDs.REQ_CUSTOM_SCAN,
                                      parameters)
        #msg, payload = await self.proto.receive_message()
        #if (self.proto.MessageIDs.OK != msg):
        #    self.logger.error("Problem with custom scan request.")
        #    raise Exception("Problem with custom scan request.")
        
    async def subscribe_to_scans(self):
        self.logger.info('Subscribing for scans.')
        await self.proto.send_message(self.proto.MessageIDs.SUBSCRIBE_TO_SCANS)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.OK != msg):
            self.logger.error("Problem with subscribing to scans.")
            raise Exception("Problem with subscribing to scans.")
    
    async def unsubscribe_from_scans(self):
        self.logger.info('Unsubscribing from scans.')
        await self.proto.send_message(self.proto.MessageIDs.UNSUBSCRIBE_FROM_SCANS)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.OK != msg):
            self.logger.error("Problem with unsubscribing from scans.")
            raise Exception("Problem with unsubscribing from scans.")
        
    async def configure_acquisition(self, config):
        self.logger.info('Configure the acquisition')
        await self.proto.send_message(self.proto.MessageIDs.CONFIG_ACQ, config)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.OK != msg):
            self.logger.error("Problem with configuring acquisition.")
            raise Exception("Problem with configuring acquisition.")
        
    async def start_acquisition(self):
        self.logger.info('Start transferring scans from the raw file by the mock')
        await self.proto.send_message(self.proto.MessageIDs.START_ACQ)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.OK != msg):
            self.logger.error("Problem with starting acquisition.")
            raise Exception("Problem with starting acquisition.")
    
    async def stop_acquisition(self):
        self.logger.info('Stop transferring scans from the raw file by the mock')
        await self.proto.send_message(self.proto.MessageIDs.STOP_ACQ)
        msg, payload = await self.proto.receive_message()
        if (self.proto.MessageIDs.OK != msg):
            self.logger.error("Problem with stopping acquisition.")
            raise Exception("Problem with stopping acquisition.")
        
    async def listen_for_scans(self):
        async with self.acq_lock:
            self.acq_running = True
        num_acq_left = self.acq_cont.num_acq
        await self.start_next_acquisition(num_acq_left)
        
        while num_acq_left > 0:
            try:
                # The problem is that the await will hang here
                msg, payload = \
                    await asyncio.wait_for(self.proto.receive_message(),
                                           timeout=0.001)
                if (self.proto.MessageIDs.FINISHED_ACQ == msg):
                    self.logger.info('Received finished acquisition message.')
                    self.algo_sync.acq_end.set()
                    num_acq_left -= 1
                    await self.start_next_acquisition(num_acq_left)
                elif (self.proto.MessageIDs.SCAN_TX == msg):
                    self.algo_sync.rec_scan_queue.put(payload)
                elif (self.proto.MessageIDs.ERROR == msg):
                    self.logger.info('Received error message.')
                    self.algo_sync.error.set()
                    break;
                else:
                    # TODO - raise exception
                    pass
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                self.logger.error(e)
                break
                
        async with self.acq_lock:
            self.acq_running = False
        self.logger.info(f'Exited listening for scans loop')
        
    async def listen_for_messages(self):
        self.listening = True
        while self.listening:
            msg, payload = await self.proto.receive_message()
            dispatch_message(msg, payload)
            
    async def dispatch_message(self, msg, payload):
        if (self.proto.MessageIDs.FINISHED_ACQ == msg):
            pass
        elif (self.proto.MessageIDs.SCAN_TX == msg):
            self.algo_sync.rec_scan_queue.put(payload)
        elif ((self.proto.MessageIDs.OK == msg) or
              (self.proto.MessageIDs.SERVER_SW_VER == msg) or
              (self.proto.MessageIDs.SERVER_PROTO_VER == msg) or
              (self.proto.MessageIDs.AVAILABLE_INSTR == msg) or
              (self.proto.MessageIDs.INSTR_INFO == msg) or
              (self.proto.MessageIDs.POSSIBLE_PARAMS == msg)):
            async with self.resp_cond:
                self.resp = (msg, payload)
                self.resp_cond.notify()
        else:
            pass
            
    def acquisition_finished(self):
        # Do all actions related to acquisition finishing
        pass
        
    async def wait_for_response(self):
        async with self.resp_cond:
            await self.resp_cond.wait()
            received_resp, resp_payload = self.resp
            self.resp = None
        return received_resp, resp_payload
                
    async def listen_for_scan_requests(self):
        self.logger.info('Start listening for scan requests')
        sleep = True
        acq_running = True
        async with self.acq_lock:
            self.acq_running = True
        while acq_running or not self.algo_sync.scan_req_queue.empty():
            if sleep:
                await asyncio.sleep(0.05)
            try:
                request = self.algo_sync.scan_req_queue.get_nowait()
                await self.request_scan(request)
                sleep = False
            except Empty:
                sleep = True
                
            async with self.acq_lock:
                acq_running = self.acq_running
        self.logger.info(f'Exited listening for requests loop')
        
    def run_async_as_sync(self, coroutine):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coroutine())
        return result
        
    async def wait_for_acquisition_start(self):
        self.logger.info('Waiting for acquisition to start...')
        is_set = False
        while (not is_set):
            is_set = self.algo_sync.move_to_next_acq.is_set()
            await asyncio.sleep(0.05)
        self.algo_sync.move_to_next_acq.clear()
        
    async def start_next_acquisition(self, num_acq_left):
        if 0 != num_acq_left:
            await self.wait_for_acquisition_start()
            await self.start_acquisition()