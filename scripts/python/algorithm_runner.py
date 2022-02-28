import asyncio
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
import multiprocessing
from queue import Empty, Full

class AlgorithmSync:
    
    def __init__ (self):
        self.rec_scan_queue = multiprocessing.Manager().Queue()
        self.scan_req_queue = multiprocessing.Manager().Queue()
        self.acq_end = multiprocessing.Manager().Event()
        self.move_to_next_acq = multiprocessing.Manager().Event()
        self.error = multiprocessing.Manager().Event()

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
        REQUEST_ACQUISITION_START = 5
        REQUEST_ACQUISITION_STOP = 6
        ERROR = 7
    
    def __init__(self, algorithm, method, sequence, algo_sync, app_cb, loop):
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
        self.algorithm = algorithm
        self.method = method
        self.sequence = sequence
        self.algo_sync = algo_sync
        
        #TODO - This should be reviewed
        self.acquisition_finishing = False
        self.app_cb = app_cb
        self.loop = loop
        
    def configure_algorithm(self, methods, 
                            sequence, rx_scan_format, 
                            req_scan_format):
        self.algorithm.configure_algorithm(self.get_scan,
                                           self.request_scan,
                                           self.start_acquisition)
        success = \
            self.algorithm.validate_scan_formats(rx_scan_format, req_scan_format)
        success = \
            self.algorithm.validate_methods_and_sequence(methods, sequence)
        return success
        
    def get_algorithm_process(self):
        loop = asyncio.get_event_loop()
        executor = ProcessPoolExecutor()
        self.algorithm_process = \
            loop.run_in_executor(executor, self.algorithm.algorithm_body)
        return self.algorithm_process
        
    def request_scan(self, request):
        self.algo_sync.scan_req_queue.put(request)
        
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
        for acquisition in self.algorithm.ACQUISITION_SEQUENCE:
            acquisition.pre_acquisition()
            # Start the acquisition
            await self.loop.acquisition.intra_acquisition()
            
    