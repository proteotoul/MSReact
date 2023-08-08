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
from pathlib import Path
import json
        
class AlgorithmManager:
    """
    This module is responsible for running the algorithms

    ...

    Attributes
    ----------
    app_cb : func
        Callback function to forward messages to the application from the 
        AlgorithmManager
    
    """
   
    RELEASES = []
    PROTO_ALGORITHMS = []
    
    ALGO_LISTS = { 'releases' : RELEASES,
                   'prototypes' : PROTO_ALGORITHMS }
                   
    TRANSFER_REGISTER = '\\transfer_register.json'
    TRANSFER_REGISTER_DEFAULTS = {"KEY" : "value"}
    
    
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
        """Collects the algorithm names for a given algorithm type

        Parameters
        ----------
        algo_type : str
            The type of algorithms for which the names are necessary to be 
            retreived. These are currently "releases" and "prototypes".

        Returns
        -------
        list
            List of strings containing the names of the algorithms of the given
            type.
        """
        return [Algorithm.ALGORITHM_NAME 
                for Algorithm, conf in self.ALGO_LISTS[algo_type]]
        
    def find_by_name(self, name):
        """Retreive an algorithm with a given name

        Parameters
        ----------
        name : str
            The name of the algorithm to retreive.

        Returns
        -------
        Algorithm
            Returns an algorithm class if the algorithm is found by name, 
            otherwise it returns None.
        """      
        found_algorithm = False
         
        for key in self.ALGO_LISTS:
            list_to_search = self.ALGO_LISTS[key]
            for i in range(len(list_to_search)):
                if name == list_to_search[i][0].ALGORITHM_NAME:
                    found_algorithm = True
                    return list_to_search[i]
        if not found_algorithm:
            return None
            
    def discover_algorithms(self):
        """Search through the algorithms folder for algorithms and store them
           based on which subfolder they were found in."""
        current_dir = os.getcwd() + '\\pymsreact\\algorithms'
        module_infos = pkgutil.iter_modules([current_dir])
        for info in module_infos:
            if info.ispkg:
                sub_infos = pkgutil.iter_modules([current_dir + '\\' + info.name])
                for subinfo in sub_infos:
                    import_name = 'algorithms.' + info.name + '.' + subinfo.name
                    module = importlib.import_module(import_name)
                    for name, value in inspect.getmembers(module):
                        #name, value = member
                        if (inspect.isclass(value) and 
                            issubclass(value, Algorithm) and
                            value is not Algorithm):
                            fconf = \
                                self.__validate_fconf(current_dir + '\\'
                                                      + info.name + '\\'
                                                      + subinfo.name
                                                      + '.hocon')
                            self.ALGO_LISTS[info.name].append((value, fconf))
    
    def select_algorithm(self, algorithm, fconf, instrument_info):
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
        selected_algorithm, default_fconf = self.find_by_name(algorithm)

        if selected_algorithm is not None:
            
            self.algorithm = selected_algorithm()
            
            for acquisition in selected_algorithm.ACQUISITION_SEQUENCE:
                if instrument_info != acquisition.instrument.instrument_name:
                    success = False
                    self.logger.error(f'Available instrument {instrument_info}' +
                                      f' not compatible with {selected_algorithm}.')
                    break
                    
            if self.__validate_fconf(fconf) is not None:
                self.fconf = fconf
            else:
                self.fconf = default_fconf # If it's None it's fine
                
        else:
            success = False
            self.logger.error(f'Algorithm {algorithm} cannot be selected.')
        return success
        
    def acquisition_ended(self):
        """Method to signal to the algorithm that the instrument 
        finished with the acquisition."""
        self.acq_in_q.put((AcqMsgIDs.ACQUISITION_ENDED, None))
        
    def acquisition_file_download_finished(self, file_path):
        self.acq_in_q.put((AcqMsgIDs.RAW_FILE_DOWNLOAD_FINISHED, file_path))

    def received_recent_raw_file_names(self, raw_file_names):
        self.acq_in_q.put((AcqMsgIDs.RECEIVED_RAW_FILE_NAMES, raw_file_names))
        
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
        no_error = True
        try:
            loop = asyncio.get_running_loop()
            acq_req_task = loop.create_task(self.__process_acquisition_requests())
            await self.__execute_algorithm(loop)
        except Exception as e:
            self.logger.error(f'An exception occured:')
            traceback.print_exc()
            no_error = False
        # Wait for the _process_acquisition_requests task to finish.
        self.listening.set()
        await acq_req_task
        return no_error
        
    def __validate_fconf(self, fconf):
        if fconf is not None:
            file = Path(fconf)
            validated_fconf = \
                fconf if (file.is_file() and file.suffix == '.hocon') else None
        else:
            validated_fconf = fconf
        return validated_fconf
            
    async def __execute_algorithm(self, loop):
        """Private method, runs the acquisitions in sequence within an algorithm.
        
        Parameters
        ----------
        loop : asyncio.loop
            The asyncio loop to execute the acquisition tasks on.
        
        """
        try:
            # Create transfer register
            transfer_register = os.getcwd() + self.TRANSFER_REGISTER
            #if not os.path.isfile(transfer_register):
            with open(transfer_register, 'w') as f:
                json.dump(self.TRANSFER_REGISTER_DEFAULTS, f)
            
            i = 0
            for acquisition in self.algorithm.acquisition_sequence:
                self.logger.info(f'Running acquisition sequence: {i}')
                self.current_acq = acquisition
                await loop.run_in_executor(self.executor,
                                           acquisition_process, 
                                           acquisition.__module__,
                                           acquisition.__name__,
                                           self.acq_in_q,
                                           self.acq_out_q,
                                           self.fconf,
                                           transfer_register)
            self.logger.info(f'Algorithm execution ended.')
        finally:
            # Remove transfer register
            if os.path.isfile(transfer_register):
                os.remove(transfer_register)
        
                                       
    async def __process_acquisition_requests(self):
        """Private method, listens to requests from the acquisitions and 
        forwards them to the application."""
        try:
            self.logger.info(f'Process acquisition requests function entered.')
            while True:
                try:
                    await self.__process_queue_items()
                except Empty:
                    if self.listening.is_set():
                        break
                await asyncio.sleep(0.001)
            self.logger.info(f'Process acquisition requests loop exited.')
        except Exception as e:
            self.logger.error(f'An exception occured:')
            traceback.print_exc()
            
    async def __process_queue_items(self):
        item = self.acq_out_q.get_nowait()
        if isinstance(item, logging.LogRecord):
            logger = logging.getLogger(item.name)
            logger.handle(item)
        else:
            await self.app_cb(*item)