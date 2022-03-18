from algorithm_list import AlgorithmList
import asyncio
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import multiprocessing
from multiprocessing import Manager
import multiprocessing.managers as m
import threading
import logging
from queue import Empty, Full
from acquisition import AcqMsgIDs, acquisition_process
import traceback

import dill

class MyManager(m.BaseManager):
    pass

class AlgorithmSync:
    
    def __init__ (self):
        self.rec_scan_queue = multiprocessing.Manager().Queue()
        self.scan_req_queue = multiprocessing.Manager().Queue()
        self.acq_end = multiprocessing.Manager().Event()
        self.move_to_next_acq = multiprocessing.Manager().Event()
        self.error = multiprocessing.Manager().Event()
        
        
class CallbackIds(Enum):
    REQUEST_SCAN = 1
    FETCH_RECEIVED_SCAN = 2
    REQUEST_REPEATING_SCAN = 3
    CANCEL_REPEATING_SCAN = 4
    ERROR = 5
    REQUEST_ACQUISITION_START = 6
    REQUEST_ACQUISITION_STOP = 7
        
class AlgorithmRunner:
    """
    This module runs the algorithms

    ...

    Attributes
    ----------
    algorithm : Algorithm
        The algorithm that needs to be executed
    method: Dict
        The acquisition method
    sequence: Dict
        The acquisition sequence
        
    Methods
    -------
    configure_algorithm:
        Configures the algorithm
    run_algorithm:
        Starts running the algorithm
    stop_algorithm:
        Stops running the algorithm
    """

    """Default cycle interval - TODO: This is only for mock."""
    DEFAULT_CYCLE_INTERVAL = 10
    
    class CallbackIds(Enum):
        REQUEST_SCAN = 1
        FETCH_RECEIVED_SCAN = 2
        REQUEST_REPEATING_SCAN = 3
        CANCEL_REPEATING_SCAN = 4
        ERROR = 5
        REQUEST_ACQUISITION_START = 6
        REQUEST_ACQUISITION_STOP = 7
        
    
    #def __init__(self, algorithm, method, sequence, algo_sync, app_cb):
    def __init__(self, app_cb):
        """
        Parameters
        ----------
        algorithm : ALGORITHM
            Algorithm to execute by algorithm executer
        rx_scan_format : dict
            The format in which the scans will be received from the Mass 
            Spectrometer instrument
        req_scan_format : dict
            The format in which a scan can be requested from the Mass 
            Spectrometer instrument
        """
        #self.algorithm = algorithm
        #self.method = method
        #self.sequence = sequence
        #self.algo_sync = algo_sync
        
        self.algo_list = AlgorithmList()
        
        #TODO - This should be reviewed
        self.acquisition_finishing = False
        self.app_cb = app_cb
        #self.loop = loop
        
        self.acq_end_internal = threading.Event()
        self.acq_end_external = multiprocessing.Manager().Event()
        self.rec_scan_queue = multiprocessing.Manager().Queue()
        self.req_queue = multiprocessing.Manager().Queue()
        
        self.logger = logging.getLogger(__name__)
        
        self.executor = ProcessPoolExecutor(max_workers=3)
        
        
        self.acq_in_q = multiprocessing.Manager().Queue()
        self.acq_out_q = multiprocessing.Manager().Queue()
        
    def select_algorithm(self, algorithm, instrument_info):
        self.logger.info(f'Selecting algorithm {algorithm}')
        success = True
        selected_algorithm = self.algo_list.find_by_name(algorithm)

        if selected_algorithm is not None:
            
            self.algorithm = selected_algorithm()
            
            for acquisition in selected_algorithm.ACQUISITION_SEQUENCE:
                if instrument_info != acquisition.instrument.instrument_name:
                    success = False
                    self.logger.error(f'Available instrument {instrument_info}' +
                                      f' not compatible with {selected_algorithm}.')
                    break
        else:
            success = False
            self.logger.error(f'Algorithm {algorithm} cannot be selected.')
        return success
        
    def acquisition_ended(self):
        self.acq_in_q.put((AcqMsgIDs.ACQUISITION_ENDED, None))
        #self.logger.info(f'Acquisition ended. Queue size: {self.acq_in_q.qsize()}')
        
    def deliver_scan(self, scan):
        #self.logger.info(f'Received scan. Queue size: {self.acq_in_q.qsize()}')
        self.acq_in_q.put((AcqMsgIDs.SCAN, scan))
        #self.logger.info(f'Received scan. Queue size: {self.acq_in_q.qsize()}')
    
    def instrument_error(self):
        self.acq_in_q.put((AcqMsgIDs.ERROR, None))
        #self.logger.info(f'Error indication received from instrument side. Queue size: {self.acq_in_q.qsize()}')
        
    def request_scan(self, request):
        self.post_request(self.CallbackIds.REQUEST_ACQUISITION_START, None)
        
    def get_scan(self):
        try:
            if self.algo_sync.acq_end.is_set() or self.algo_sync.error.is_set():
                # Set acquisition finishing to true, so next time the queue
                # is found to be empty, an acquisition finished message is 
                # sent to the algorithm.
                self.acquisition_finishing = True
            scan = (self.algorithm.AcquisitionStatus.scan_available,
                    self.algo_sync.rec_scan_queue.get_nowait())
        except Empty:
            if self.acquisition_finishing:
                self.algo_sync.acq_end.clear()
                scan = (self.algorithm.AcquisitionStatus.acquisition_finished,
                        None)
                self.acquisition_finishing = False
            else:
                scan = (self.algorithm.AcquisitionStatus.scan_not_available, None)
        return scan
        
    def start_acquisition(self):
        self.algo_sync.move_to_next_acq.set()
        
    async def run_algorithm(self):
        # Note: Consider handling runtime error that can be raised if there is
        # no active event loop
        
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.process_algorithm_requests())
            await self.execute_algorithm(loop)
            #await asyncio.gather(self.execute_algorithm(loop),
            #                     self.process_algorithm_requests(loop))
        except Exception as e:
            traceback.print_exc()
            
    async def execute_algorithm(self, loop):
        i = 0
        for acquisition in self.algorithm.acquisition_sequence:
            self.logger.info(f'Running acquisition sequence: {i}')
            self.current_acq = acquisition
            await loop.run_in_executor(self.executor,
                                       acquisition_process, 
                                       acquisition.__module__,
                                       acquisition.__name__,
                                       self.acq_in_q, 
                                       self.acq_out_q)
            #await self.piclke_this_if_you_can(acquisition, loop)
        self.logger.info(f'Algorithm execution ended.')
                                       
    async def process_algorithm_requests(self):
        try:
            self.logger.info(f'Process algo requests function entered.')
            while not self.acq_end_external.is_set():
                #self.logger.info(f'Try to get request.')
                try:
                    request, args = self.acq_out_q.get_nowait()
                    self.logger.info(f'Got request from algorithm: {request}')
                    await self.app_cb(request, args)
                except Empty:
                    pass
                await asyncio.sleep(0.01)
            self.logger.info(f'Process algo requests loop exited.')
        except Exception as e:
            traceback.print_exc()
            
    async def piclke_this_if_you_can(self, acquisition, loop):
        # Run pre-acquisition activities
        self.logger.info('Running pre acquisition.')
        algo_proc = loop.run_in_executor(self.executor,
                                         acquisition.pre_acquisition)
                                         
        await algo_proc
        
        # Prepare intra-acquisition activities to be ran in a thread
        # Start the thread, request acquisition start
        self.logger.info('Starting intra acquisition thread.')
        #intra_acq_thread = \
        #    threading.Thread(name='intra_acquisition_thread',
        #                     target=acquisition.intra_acquisition,
        #                     args=(self.is_acquisition_ended),
        #                     daemon=True)
        #intra_acq_thread.start()
        #self.logger.info('Request acquisition start')
        #self.post_request(self.CallbackIds.REQUEST_ACQUISITION_START,
        #                  acquisition.acquisition_workflow)
        
        # Wait for acquisition to finish and signal it to the thread when it happens
        #self.acq_end_external.wait()
        #self.acq_end_internal.set()
        #intra_acq_thread.join()
        
        algo_proc=  loop.run_in_executor(self.executor,
                                         acquisition.post_acquisition)
                                   
        await algo_proc
            
    def run_acquisition(self):
        # Run pre-acquisition activities
        self.logger.info('Running pre acquisition.')
        self.current_acq.pre_acquisition()
        
        # Prepare intra-acquisition activities to be ran in a thread
        # Start the thread, request acquisition start
        self.logger.info('Starting intra acquisition thread.')
        intra_acq_thread = \
            threading.Thread(name='intra_acquisition_thread',
                             target=self.current_acq.intra_acquisition,
                             args=(self.is_acquisition_ended,),
                             daemon=True)
        intra_acq_thread.start()
        self.logger.info('Request acquisition start')
        self.post_request(self.CallbackIds.REQUEST_ACQUISITION_START,
                          self.current_acq.acquisition_workflow)
        self.logger.info('Requested acquisition start')
        # Wait for acquisition to finish and signal it to the thread when it happens
        self.acq_end_external.wait()
        self.acq_end_internal.set()
        intra_acq_thread.join()
        
        self.current_acq.post_acquisition()
    
    def is_acquisition_ended(self):
        return self.acq_end_internal.is_set()
        
    def post_request(self, request, args):
        self.req_queue.put((request, args))
        
        
def test_cb(request, args):
    print(f'Request: {request}, args: {args}')
    
def pickle_empty_func():
    pass
    
def algorithm_process(acquisition, queue):
    # Run pre-acquisition activities
    acquisition.pre_acquisition()
    
    intra_acq_thread = \
        threading.Thread(name='intra_acquisition_thread',
                         target=acquisition.intra_acquisition,
                         args=(self.is_acquisition_ended,),
                         daemon=True)
    intra_acq_thread.start()
    self.post_request(self.CallbackIds.REQUEST_ACQUISITION_START,
                      self.current_acq.acquisition_workflow)
    # Wait for acquisition to finish and signal it to the thread when it happens
    self.acq_end_external.wait()
    self.acq_end_internal.set()
    intra_acq_thread.join()
    
    acquisition.post_acquisition()
    
    


if __name__ == '__main__':
    algo_runner = AlgorithmRunner(test_cb)
    result = algo_runner.select_algorithm('listen_test', "Tribid")
    
    dill.detect.badtypes(algo_runner.run_acquisition, depth=3)