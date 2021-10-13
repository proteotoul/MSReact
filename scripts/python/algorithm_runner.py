import asyncio
from concurrent.futures import ProcessPoolExecutor
import enum
import multiprocessing
from queue import Empty, Full

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
    
    class ConfigErrors(enum.Enum):
        no_error        = 0
        method_error    = 1
        sequence_error  = 2
    
    def __init__(self, algorithm, method, sequence, scan_queue, req_queue):
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
        self.scan_queue = scan_queue
        self.req_queue = req_queue
        
    def configure_and_validate_algorithm(self, methods, sequence, rx_scan_format, req_scan_format):
        self.algorithm.configure_algorithm(self.get_scan, self.request_scan)
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
        self.req_queue.put(request)
        
    def get_scan(self):
        try:
            scan = self.scan_queue.get_nowait()
        except Empty:
            scan = None
        return scan