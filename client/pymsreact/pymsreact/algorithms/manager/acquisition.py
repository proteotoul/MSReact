from .ms_instruments.ms_instrument import MassSpectrometerInstrument
from . import acquisition_workflow as aw
from . import acquisition_settings as acqs
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

class AcqMsgIDs(Enum):
    """
    Enum of acquisition message ids
    """
    SCAN = 1
    REQUEST_SCAN = 2
    FETCH_RECEIVED_SCAN = 3
    REQUEST_REPEATING_SCAN = 4
    CANCEL_REPEATING_SCAN = 5
    READY_FOR_ACQUISITION_START = 6
    REQUEST_ACQUISITION_STOP = 7
    ACQUISITION_ENDED = 8
    ERROR = 9
    ENABLE_PLOT = 10
    DISABLE_PLOT = 11
    
class AcqStatIDs(Enum):
    """
    Enum of acquisition status ids
    """
    ACQUISITION_IDLE = 1
    ACQUISITION_PRE_ACQUISITION = 2
    ACQUISITION_RUNNING = 3
    ACQUISITION_ENDED_NORMAL = 4
    ACQUISITION_ENDED_ERROR = 5
    ACQUISITION_POST_ACQUISITION = 6

DEFAULT_NAME = "Default Acquisition"

class Acquisition:
    """
    Base class for mass spectrometer acquisitions, implementing several methods
    to ease the development of new acquisition methods.

    ...

    Attributes
    ----------
    queue_in : queue.Queue
       Input queue through which the acquisition receives messages from the 
       algorithm runner
    queue_out : queue.Queue
       Output queue through which the acquisition can send messages to the 
       algorithm runner
    
    """


    def __init__(self, queue_in, queue_out):
        """
        Parameters
        ----------
        queue_in : queue.Queue
           Input queue through which the acquisition receives messages from the 
           algorithm runner
        queue_out : queue.Queue
           Output queue through which the acquisition can send messages to the 
           algorithm runner
        """
        self.name = DEFAULT_NAME
        
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.scan_queue = queue.Queue()
        self.status_lock = threading.Lock()
        
        self.instrument = MassSpectrometerInstrument()
        self.settings = acqs.AcquisitionSettings()
        self.status = AcqStatIDs.ACQUISITION_IDLE
        
        # Since the acquisition objects are instantiated in separate processes,
        # logging needs to be initialized. The log messages from the acquisition
        # are sent through the queue_out to the main process and the records are 
        # being handled there.          
        queue_handler = logging.handlers.QueueHandler(queue_out)
        root = logging.getLogger()
        # Remove the default stream handler to avoid duplicate printing
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                root.removeHandler(handler)
        root.addHandler(queue_handler)
        root.setLevel(logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        
    def fetch_received_scan(self):
        """Try to fetch a scan from the received scans queue. If the queue is 
        empty it returns None
        
        Returns:
            dict: Scan in the form of a dictionary
        """
        scan = None
        try:
            scan = self.scan_queue.get_nowait()
        except queue.Empty:
            time.sleep(0.001)
        return scan
        
    def signal_ready_for_acquisition(self):
        """Signals to the algorithm runner, that the acquisition is finished 
        with the pre-acquisition steps and ready for the start of the
        acquisition method"""
    
        # if it's listening workflow, then this should do nothing
        self.queue_out.put((AcqMsgIDs.READY_FOR_ACQUISITION_START, 
                            self.settings))
                            
    def request_acquisition_stop(self):
        """Requests from the algorithm runner to stop the acquisition"""
        self.queue_out.put((AcqMsgIDs.REQUEST_ACQUISITION_STOP, None))
        
    def request_custom_scan(self, request, request_id = None):
        """Requests a custom scan with the given parameters
        Parameters
        ----------
        request : dict
            Custom scan request parameters organised into a string-string 
            dictionary in the form of parameter_name : value, eg. 
            "PrecursorMass" : "800.25" """
        # TODO: Should check if the int is 64 bit length or not.
        if ((request_id is not None) and (isinstance(request_id, int))):
            request.update({'REQUEST_ID' : request_id})

        self.queue_out.put((AcqMsgIDs.REQUEST_SCAN, request))       
        
    def request_repeating_scan(self, request):
        """Request a repeating scan with the given parameters
        Parameters
        ----------
        request : dict
            Repeating scan request parameters organised into a string-string 
            dictionary in the form of parameter_name : value, eg. 
            "PrecursorMass" : "800.25" """
        self.queue_out.put((AcqMsgIDs.REQUEST_REPEATING_SCAN, request))
        
    def cancel_repeating_scan(self, request):
        """Cancel a repeating scan with the given parameters
        Parameters
        ----------
        request : dict
            Repeating scan request parameters to cancel organised into a
            string-string dictionary in the form of parameter_name : value, eg. 
            "PrecursorMass" : "800.25" """
        self.queue_out.put((AcqMsgIDs.CANCEL_REPEATING_SCAN, request))
        
    def signal_error_to_runner(self, error_msg):
        """Signal error to the algorithm runner
        Parameters
        ----------
        error_msg : str
            Error message to be forwarded to the algorithm runner """
        self.queue_out.put((AcqMsgIDs.ERROR, error_msg))
        
    def get_acquisition_status(self):
        """Get the status of the current acqusition
        
        Returns:
            AcqStatIDs: The current status of the acquisition
        """
        with self.status_lock:
            status = self.acquisition_status
        return status
        
    def update_acquisition_status(self, new_status):
        """Update the acquisition status to the given status
        Parameters
        ----------
        new_status : AcqStatIDs
            New status to update the current status to"""
        # TODO - check if the new_status is valid element of the Enum
        with self.status_lock:
            self.acquisition_status = new_status
        
    def wait_for_end_or_error(self):
        """Wait until the acquisition ends or until an error occurs"""
        while True:
            try:
                cmd, payload = self.queue_in.get_nowait()
            except queue.Empty:
                time.sleep(0.001)
                continue
            if AcqMsgIDs.SCAN == cmd:
                self.scan_queue.put(payload)
            elif AcqMsgIDs.ACQUISITION_ENDED == cmd:
                self.update_acquisition_status(AcqStatIDs.ACQUISITION_ENDED_NORMAL)
                break
            elif AcqMsgIDs.ERROR == cmd:
                self.update_acquisition_status(AcqStatIDs.ACQUISITION_ENDED_ERROR)
                break
            else:
                pass
        
    @abstractmethod
    def pre_acquisition(self):
        """Abstract method to be overriden with steps to execute before an
            acquisition"""
        pass
        
    @abstractmethod
    def intra_acquisition(self):
        """Abstract method to be overriden with steps to execute during an
           acquisition"""
        pass
        
    @abstractmethod
    def post_acquisition(self):
        """Abstract method to be overriden with steps to execute after an
           acquisition"""
        pass
        
def acquisition_process(module_name, acquisition_name, queue_in, queue_out):
    """This method is responsible for executing the pre-, intra- and 
       post-acquisition steps. The method is ran in a separate proccess.

    Parameters
    ----------
    module_name : str
        Name of the module from which the acquisition class will be imported.
    acquisition_name : str
        Name of the acquisition class to be executed by the acquisition_process.
    queue_in : queue.Queue
       Input queue through which the acquisition receives messages from the 
       algorithm runner
    queue_out : queue.Queue
       Output queue through which the acquisition can send messages to the 
       algorithm runner
    """

    module = importlib.import_module(module_name)
    class_ = getattr(module, acquisition_name)
    acquisition = class_(queue_in, queue_out)
    
    acquisition.logger.info('Running pre acquisition.')
    acquisition.update_acquisition_status(AcqStatIDs.ACQUISITION_PRE_ACQUISITION)
    acquisition.pre_acquisition()
    
    # Prepare intra-acquisition activities to be ran in a thread
    # Start the thread, request acquisition start
    acquisition.logger.info('Starting intra acquisition thread.')
    intra_acq_thread = \
        threading.Thread(name='intra_acquisition_thread',
                         target=acquisition.intra_acquisition,
                         daemon=True)
    acquisition.update_acquisition_status(AcqStatIDs.ACQUISITION_RUNNING)
    # TODO: The start of the intra acquisition thread could be done before or after
    # the signaling to the client. Should be decided. Possible synchronisation of start
    # could be considered.
    # intra_acq_thread.start()
    acquisition.logger.info('Signal "Ready for acquisition".')
    acquisition.signal_ready_for_acquisition()
    intra_acq_thread.start()
    # Wait for acquisition to finish and signal it to the thread when it happens
    # TODO: This is okay for now, but should listen for error messages during
    #       pre and post acquisition too
    acquisition.wait_for_end_or_error()
    acquisition.logger.info('Received message to stop the acquisition.')
    intra_acq_thread.join()
    # TODO: For now, it is the user's responsibility to check whether an error occured during
    #       the acquisition and decide what kind of activities to carry out in each case.
    acquisition.post_acquisition()