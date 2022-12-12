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
from enum import Enum, IntEnum
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
    REQUEST_DEF_SCAN_PARAM_UPDATE = 10
    SET_TX_SCAN_LEVEL = 11
    ENABLE_PLOT = 12
    DISABLE_PLOT = 13
    REQUEST_RAW_FILE_NAME = 14
    
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
    
class ScanFields(IntEnum):
    """
    Enum to decode receive scans
    """
    CENTROID_COUNT = 0
    CENTROIDS = 1
    DETECTOR_NAME = 2
    MS_SCAN_LEVEL = 3
    PRECURSOR_CHANGE = 4
    PRECURSOR_MASS = 5
    RETENTION_TIME = 6
    SCAN_NUMBER = 7
    
class CentroidFields(IntEnum):
    CHARGE = 0
    INTENSITY = 1
    IS_EXCEPTIONAL = 2
    IS_FRAGMENTED = 3
    IS_MERGED = 4
    IS_MONOISOTOPIC = 5
    IS_REFERENCED = 6
    MZ = 7

DEFAULT_NAME = "Default Acquisition"
DEFAULT_SCAN_TX_INTERVAL = [1, 1]

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
        self.scan_tx_interval = DEFAULT_SCAN_TX_INTERVAL
        
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
        
    def configure(self, fconf):
        if fconf is not None:
            with open(fconf) as f:
                self.config = json.load(f)
        else:
            self.config = None
            
        self.logger.info('Acquisition was configured with the following ' +
                         f'configuration: {self.config}')
    
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
        
    def request_def_scan_param_update(self, params):
        """Request the update of default scan parameters. When a custom scan is 
           requested, only the scan parameters that are specified in the request 
           are updated, the rest of the parameters stay the default values. With
           this request the default parameters can be overwritten, so they 
           don't need to be specified at each request if they stay the same.
        Parameters
        ----------
        params : dict
            Repeating scan request parameters to cancel organised into a
            string-string dictionary in the form of parameter_name : value, eg. 
            "PrecursorMass" : "800.25" """
        self.queue_out.put((AcqMsgIDs.REQUEST_DEF_SCAN_PARAM_UPDATE, params))
        
    def set_tx_scan_interval(self):
        """Sets the order of MS scans to be transmitted by the Mock server. In
           case the client is not used with the Mock, this command has no
           effect.
        """
        self.queue_out.put((AcqMsgIDs.SET_TX_SCAN_LEVEL, self.scan_tx_interval))
        
    def get_raw_file_name(self):
        self.queue_out.put((AcqMsgIDs.REQUEST_RAW_FILE_NAME, None))
        
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
        
def acquisition_process(module_name,
                        acquisition_name,
                        queue_in,
                        queue_out,
                        fconf):
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
    
    acquisition.configure(fconf)
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
    acquisition.set_tx_scan_interval()
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