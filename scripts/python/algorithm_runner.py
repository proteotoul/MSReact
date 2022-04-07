from algorithm_list import AlgorithmList
import asyncio
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import logging
from queue import Empty, Full
from acquisition import AcqMsgIDs, acquisition_process
import traceback
        
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
        
        # Instantiate the algorithm list
        self.algo_list = AlgorithmList()
        
        # Register app callback and logging
        self.app_cb = app_cb
        self.logger = logging.getLogger(__name__)
        
        # Create process pool, listening event and queues for multiprocessing
        self.executor = ProcessPoolExecutor(max_workers=3)
        self.listening = multiprocessing.Manager().Event()
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
        
    def deliver_scan(self, scan):
        self.acq_in_q.put((AcqMsgIDs.SCAN, scan))
    
    def instrument_error(self):
        self.acq_in_q.put((AcqMsgIDs.ERROR, None))
        
    async def run_algorithm(self):
        # Note: Consider handling runtime error that can be raised if there is
        # no active event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.process_acquisition_requests())
            await self.execute_algorithm(loop)
        except Exception as e:
            traceback.print_exc()
        self.listening.set()
            
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
        self.logger.info(f'Algorithm execution ended.')
                                       
    async def process_acquisition_requests(self):
        try:
            self.logger.info(f'Process acquisition requests function entered.')
            while not self.listening.is_set():
                try:
                    request, args = self.acq_out_q.get_nowait()
                    self.logger.info(f'Got request from algorithm: {request} ' +
                                     f'payload: {args}')
                    await self.app_cb(request, args)
                except Empty:
                    pass
                await asyncio.sleep(0.01)
            self.logger.info(f'Process acquisition requests loop exited.')
        except Exception as e:
            traceback.print_exc()