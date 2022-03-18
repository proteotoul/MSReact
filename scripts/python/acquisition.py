from ms_instrument import MassSpectrometerInstrument
import acquisition_workflow as aw
import threading
import multiprocessing
import logging
import logging.config
import importlib
import inspect
import time
import json
import queue
from enum import Enum
from abc import abstractmethod
from concurrent.futures import ProcessPoolExecutor
import asyncio
import sys

class AcqMsgIDs(Enum):
    SCAN = 1
    REQUEST_SCAN = 2
    FETCH_RECEIVED_SCAN = 3
    REQUEST_REPEATING_SCAN = 4
    CANCEL_REPEATING_SCAN = 5
    REQUEST_ACQUISITION_START = 6
    REQUEST_ACQUISITION_STOP = 7
    ACQUISITION_ENDED = 8
    ERROR = 9
    
class AcquisitionStatusIds(Enum):
    ACQUISITION_IDLE = 1
    ACQUISITION_PRE_ACQUISITION = 2
    ACQUISITION_RUNNING = 3
    ACQUISITION_ENDED_NORMAL = 4
    ACQUISITION_ENDED_ERROR = 5
    ACQUISITION_POST_ACQUISITION = 6

DEFAULT_NAME = "Default Acquisition"

class Acquisition:
    def __init__(self, queue_in, queue_out):
    #             acquisition_workflow = aw.AcquisitionWorkflow(),
    #             pre_acquisition = None,
    #             intra_acquisition = None,
    #             post_acquisition = None):
        self.name = DEFAULT_NAME
        self.instrument = MassSpectrometerInstrument()
        self.acquisition_workflow = aw.AcquisitionWorkflow(),
        self.acquisition_finished = threading.Event()
        with open("log_conf.json", "r", encoding="utf-8") as fd:
            logging.config.dictConfig(json.load(fd))
        self.logger = logging.getLogger(__name__)
        self.scan_queue = queue.Queue()
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.status_lock = threading.Lock()
        self.acquisition_status = AcquisitionStatusIds.ACQUISITION_IDLE
        
        #if acquisition_workflow.__class__ in self.instrument.supported_acquisition_workflows:
        #    self.acquisition_workflow = acquisition_workflow
        #else:
        #    raise ValueError('Acquisition workflow ' +
        #                     f'{acquisition_workflow.__name__} is not supported for ' +
        #                     f'{self.instrument.instrument_name} instrument.')
        #self.pre_acquisition = \
        #    self.default_action if pre_acquisition is None else pre_acquisition
        #self.intra_acquisition = \
        #    self.default_action if intra_acquisition is None else intra_acquisition
        #self.post_acquisition = \
        #    self.default_action if post_acquisition is None else post_acquisition
           
        
    def get_module_name(self):
        module = TestAcquisition.__module__
    
        if module == '__main__':
            filename = sys.modules[self.__module__].__file__
            module = os.path.splitext(os.path.basename(filename))[0]
        return module
        
    def fetch_received_scan(self):
        scan = None
        try:
            scan = self.scan_queue.get_nowait()
        except queue.Empty:
            pass
        return scan
        
    def start_acquisition(self):
        # if it's listening workflow, then this should do nothing
        self.queue_out.put((AcqMsgIDs.REQUEST_ACQUISITION_START,
                            self.acquisition_workflow))
        
    def request_custom_scan(self, request):
        self.queue_out.put((AcqMsgIDs.REQUEST_SCAN, request))
        
    def request_repeating_scan(self, request):
        self.queue_out.put((AcqMsgIDs.REQUEST_REPEATING_SCAN, request))
        
    def cancel_repeating_scan(self, request):
        self.queue_out.put((AcqMsgIDs.CANCEL_REPEATING_SCAN, request))
        
    def signal_error_to_runner(self, error_msg):
        self.queue_out.put((AcqMsgIDs.ERROR, error_msg))
        
    def get_acquisition_status(self):
        with self.status_lock:
            status = self.acquisition_status
        return status
    def update_acquisition_status(self, new_status):
        # TODO - check if the new_status is valid element of the Enum
        with self.status_lock:
            self.acquisition_status = new_status
        
    def wait_for_end_or_error(self):
        while True:
            try:
                cmd, payload = self.queue_in.get_nowait()
            except queue.Empty:
                time.sleep(0.1)
                continue
            if AcqMsgIDs.SCAN == cmd:
                self.scan_queue.put(payload)
            elif AcqMsgIDs.ACQUISITION_ENDED == cmd:
                self.update_acquisition_status(AcquisitionStatusIds.ACQUISITION_ENDED_NORMAL)
                break
            elif AcqMsgIDs.ERROR == cmd:
                self.update_acquisition_status(AcquisitionStatusIds.ACQUISITION_ENDED_ERROR)
                break
            else:
                pass
        
    @abstractmethod
    def pre_acquisition(self):
        pass
        
    @abstractmethod
    def intra_acquisition(self):
        pass
        
    @abstractmethod
    def post_acquisition(self):
        pass
        
        
class TestAcquisition(Acquisition):
    def pre_acquisition(self):
        pass
        
    def intra_acquisition(self):
        while AcquisitionStatusIds.ACQUISITION_RUNNING == self.get_acquisition_status():
            time.sleep(0.3)
            print("not yet finished so go back to sleep")
        
    def post_acquisition(self):
        pass
        
def acquisition_process(module_name, acquisition_name, queue_in, queue_out):
    module = importlib.import_module(module_name)
    class_ = getattr(module, acquisition_name)
    acquisition = class_(queue_in, queue_out)
    
    acquisition.logger.info('Running pre acquisition.')
    acquisition.update_acquisition_status(AcquisitionStatusIds.ACQUISITION_PRE_ACQUISITION)
    acquisition.pre_acquisition()
    
    # Prepare intra-acquisition activities to be ran in a thread
    # Start the thread, request acquisition start
    acquisition.logger.info('Starting intra acquisition thread.')
    intra_acq_thread = \
        threading.Thread(name='intra_acquisition_thread',
                         target=acquisition.intra_acquisition,
                         daemon=True)
    acquisition.update_acquisition_status(AcquisitionStatusIds.ACQUISITION_RUNNING)
    intra_acq_thread.start()
    acquisition.logger.info('Request acquisition start')
    acquisition.start_acquisition()
    # Wait for acquisition to finish and signal it to the thread when it happens
    # TODO: This is okay for now, but should listen for error messages during
    #       pre and post acquisition too
    acquisition.wait_for_end_or_error()
    acquisition.logger.info('Received message to stop the acquisition.')
    intra_acq_thread.join()
    if AcquisitionStatusIds.ACQUISITION_ENDED_ERROR != acquisition.get_acquisition_status():
        acquisition.post_acquisition()
    
async def test_run_acq():
    queue_in = multiprocessing.Manager().Queue()
    queue_out = multiprocessing.Manager().Queue()
    
    name = TestAcquisition.__name__
    module = inspect.getmodule(TestAcquisition)
    
    print(name)
    print(module)
    
    executor = ProcessPoolExecutor()
    loop = asyncio.get_running_loop()
    task = loop.run_in_executor(executor,
                                acquisition_process,
                                TestAcquisition.__module__,
                                TestAcquisition.__name__, 
                                queue_in, queue_out)
    
    await asyncio.gather(task, test_stop_acq(queue_in))
                               
async def test_stop_acq(queue_in):
    for i in range(5):
        await asyncio.sleep(1)
        print(f"Cycle {i} is done")
    queue_in.put((AcqMsgIDs.ACQUISITION_ENDED, None))
    

if __name__ == "__main__":
    asyncio.run(test_run_acq())
    #acq = TestAcquisition(acquisition_workflow = aw.Listening)
    #print(acq.name)