import asyncio
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import logging
from queue import Empty, Full
from .acquisition import AcqMsgIDs, acquisition_process
import traceback
import importlib
import inspect
import os
import pkgutil
from .algorithm import Algorithm
        
class AlgorithmManager:
    """
    This module is responsible for running the algorithms

    ...

    Attributes
    ----------
    app_cb : func
        Callback function to forward messages to the application from the 
        AlgorithmManager
        
    Methods
    -------
    select_algorithm:
        Method to select the algorithm to run.
    acquisition_ended:
        Method to signal to the algorithm that the instrument 
        finished with the acquisition.
    deliver_scan:
        Method to forward scans received from the instrument to the algorithm.
    instrument_error:
        Method to signal to the algorithm that the other parts of the client or
        the server encountered an error.
    run_algorithm:
        Method with which the application can start running the selected 
        algorithm.
    __execute_algorithm:
        Private method, runs the acquisitions in sequence within an algorithm.
    __process_acquisition_requests:
        Private method, listens to requests from the acquisitions and forwards
        them to the application.
    
    
    """
   
    RELEASES = []
    PROTO_ALGORITHMS = []
    
    ALGO_LISTS = { 'releases' : RELEASES,
                   'prototypes' : PROTO_ALGORITHMS }
    
    
    def __init__(self, app_cb):
        """
        Parameters
        ----------
        app_cb : func
            Callback function to forward messages to the application from the 
            AlgorithmManager
        """
        
        # Register app callback and logging
        self.app_cb = app_cb
        self.logger = logging.getLogger(__name__)
        
        # Create process pool, listening event and queues for multiprocessing
        self.executor = ProcessPoolExecutor(max_workers=3)
        self.listening = multiprocessing.Manager().Event()
        self.acq_in_q = multiprocessing.Manager().Queue()
        self.acq_out_q = multiprocessing.Manager().Queue()
        
        # Discover algorithms
        self.discover_algorithms()
        
    def get_algorithm_names(self, algo_type):
        return [Algorithm.ALGORITHM_NAME 
                for Algorithm in self.ALGO_LISTS[algo_type]]
        
    def find_by_name(self, name):
        found_algorithm = False
         
        for key in self.ALGO_LISTS:
            list_to_search = self.ALGO_LISTS[key]
            for i in range(len(list_to_search)):
                if name == list_to_search[i].ALGORITHM_NAME:
                    found_algorithm = True
                    return list_to_search[i]
        if not found_algorithm:
            return None
            
    def discover_algorithms(self):
        current_dir = os.getcwd() + '\\algorithms'
        module_infos = pkgutil.iter_modules([current_dir])
        for info in module_infos:
            if info.ispkg:
                sub_infos = pkgutil.iter_modules([current_dir + '\\' + info.name])
                for subinfo in sub_infos:
                    import_name = 'algorithms.' + info.name + '.' + subinfo.name
                    module = importlib.import_module(import_name)
                    for member in inspect.getmembers(module):
                        if (inspect.isclass(member[1]) and 
                            issubclass(member[1], Algorithm) and
                            member[1] is not Algorithm):
                            self.ALGO_LISTS[info.name].append(member[1])
    
    def select_algorithm(self, algorithm, instrument_info):
        """Method to select the algorithm to run.
        
        Parameters
        ----------
        algorithm : str
            Name of the algorithm that is selected to be run.
        instrument_info : str
            Name of the available instrument.
        """
        self.logger.info(f'Selecting algorithm {algorithm}')
        success = True
        selected_algorithm = self.find_by_name(algorithm)

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
        """Method to signal to the algorithm that the instrument 
        finished with the acquisition."""
        self.acq_in_q.put((AcqMsgIDs.ACQUISITION_ENDED, None))
        
    def deliver_scan(self, scan):
        """Method to forward scans received from the instrument to the algorithm.
        
        Parameters
        ----------
        scan : dict
            Scan that was received from the instrument (through the server) in
            the form of a dictionary.
        """
        self.acq_in_q.put((AcqMsgIDs.SCAN, scan))
    
    def instrument_error(self):
        """Method to signal to the algorithm that the other parts of the client or
        the server encountered an error."""
        self.acq_in_q.put((AcqMsgIDs.ERROR, None))
        
    async def run_algorithm(self):
        """Method with which the application can start running the selected 
        algorithm."""
        # Note: Consider handling runtime error that can be raised if there is
        # no active event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.__process_acquisition_requests())
            await self.__execute_algorithm(loop)
        except Exception as e:
            traceback.print_exc()
        self.listening.set()
            
    async def __execute_algorithm(self, loop):
        """Private method, runs the acquisitions in sequence within an algorithm.
        
        Parameters
        ----------
        loop : asyncio.loop
            The asyncio loop to execute the acquisition tasks on.
        
        """
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
                                       
    async def __process_acquisition_requests(self):
        """Private method, listens to requests from the acquisitions and forwards
        them to the application."""
        try:
            self.logger.info(f'Process acquisition requests function entered.')
            while not self.listening.is_set():
                try:
                    request, args = self.acq_out_q.get_nowait()
                    #self.logger.info(f'Got request from algorithm: {request} ' +
                    #                 f'payload: {args}')
                    await self.app_cb(request, args)
                except Empty:
                    pass
                await asyncio.sleep(0.01)
            self.logger.info(f'Process acquisition requests loop exited.')
        except Exception as e:
            traceback.print_exc()