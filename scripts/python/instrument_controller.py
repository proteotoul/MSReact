import asyncio
from multiprocessing import Queue
from protocol import Protocol
from queue import Empty, Full

class InstrumentController:
    '''
    Parameters
    ----------
    
    '''
    def __init__(self, protocol, algo_sync, acq_cont):
        self.proto = protocol
        self.algo_sync = algo_sync
        self.acq_cont = acq_cont
        self.acq_running = False
        self.acq_lock = asyncio.Lock()
        
    async def connect_to_instrument(self, uri):
        await self.proto.tl.connect(uri)
        
    async def disconnect_from_instrument():
        await self.proto.tl.disconnect()
        
    async def get_protocol_version(self):
        print('Getting protocol version')
        await self.proto.send_command(self.proto.Commands.GET_VERSION)
        cmd, payload = await self.proto.receive_command()
        if (self.proto.Commands.VERSION == cmd):
            print(f'Received version: {payload}')
        else:
            pass
            # Raise exception
        return payload
        
    async def get_possible_params(self):
        print('Getting possible parameters for requesting scans...')
        await self.proto.send_command(self.proto.Commands.GET_POSSIBLE_PARAMS)
        cmd, payload = await self.proto.receive_command()
        if (self.proto.Commands.POSSIBLE_PARAMS != cmd):
            # TODO - raise exception
            print("Response was not POSSIBLE_PARAMS command.")
        return payload
        
    async def request_scan(self, parameters):
        print(f'Requesting scans with the following parameters:\n{parameters}')
        await self.proto.send_command(self.proto.Commands.CUSTOM_SCAN, 
                                      parameters)
        
    async def subscribe_to_scans(self):
        print('Subscribing for scans.')
        await self.proto.send_command(self.proto.Commands.SUBSCRIBE_TO_SCANS)
    
    async def unsubscribe_from_scans(self):
        print('Unsubscribing from scans.')
        await self.proto.send_command(self.proto.Commands.UNSUBSCRIBE_FROM_SCANS)
        
    async def set_ms_scan_tx_level(self, level):
        print(f'Setting ms scan transfer level to {level}')
        await self.proto.send_command(self.proto.Commands.SET_MS_SCAN_TX_LEVEL)
        
    async def listen_for_scans(self):
        print('Start listening for scans')
        async with self.acq_lock:
            self.acq_running = True
        num_acq_left = self.acq_cont.num_acq
        while num_acq_left > 0:
            try:
                # The problem is that the await will hang here
                cmd, payload = \
                    await asyncio.wait_for(self.proto.receive_command(), 
                                           timeout=0.001)
                if (self.proto.Commands.FINISHED_SCAN_TX == cmd):
                    self.algo_sync.acq_end.set()
                    num_acq_left -= 1
                elif (self.proto.Commands.SCAN_TX == cmd):
                    self.algo_sync.rec_scan_queue.put(payload)
                else:
                    # TODO - raise exception
                    pass
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(e)
                break
                
        async with self.acq_lock:
            self.acq_running = False
        print(f'Exited listening for scans loop')
                
    async def listen_for_scan_requests(self):
        print('Start listening for scan requests')
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
        print(f'Exited listening for requests loop')
        
    def run_async_as_sync(self, coroutine):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(coroutine())
        return result
        
    