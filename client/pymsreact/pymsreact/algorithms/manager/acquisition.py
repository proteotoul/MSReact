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
from pprint import pprint

from pyhocon import ConfigFactory

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
    REQUEST_LAST_RAW_FILE = 15
    RAW_FILE_DOWNLOAD_FINISHED = 16
    RECEIVED_RAW_FILE_NAMES = 17
    
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
    Enum to decode received scans
    """
    ACCESS_ID = 0
    CENTROID_COUNT = 1
    CENTROIDS = 2
    DETECTOR_NAME = 3
    MS_SCAN_LEVEL = 4
    PRECURSOR_CHARGE = 5
    PRECURSOR_MASS = 6
    RETENTION_TIME = 7
    SCAN_NUMBER = 8
    
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
    
    TRANSFER_REGISTER_NAME = '.\\transfer_register.json'


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
        self.raw_file_names_lock = threading.Lock()
        self.raw_file_lock = threading.Lock()
        self.transfer_register_lock = threading.Lock()
        
        self.instrument = MassSpectrometerInstrument()
        self.settings = acqs.AcquisitionSettings()
        self.status = AcqStatIDs.ACQUISITION_IDLE
        self.recent_raw_file_names = []
        self.last_raw_file = ''
        
        self.transfer_register = {}
        self.transfer_register_file = ''
        
        # Since the acquisition objects are instantiated in separate processes,
        # logging needs to be initialized. The log messages from the acquisition
        # are sent through the queue_out to the main process and the records are 
        # being handled there.          
        queue_handler = logging.handlers.QueueHandler(queue_out)
        root = logging.getLogger()
        # Remove the default stream handler to avoid duplicate printing
        no_que_handler_exists = True
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                root.removeHandler(handler)
            if isinstance(handler, logging.handlers.QueueHandler):
                no_que_handler_exists = False
        if no_que_handler_exists:
            root.addHandler(queue_handler)
            root.setLevel(logging.DEBUG)
            
        self.logger = logging.getLogger(__name__)
        
    def configure(self, fconf, transfer_register):
        if fconf is not None:
            configtree = ConfigFactory.parse_file(fconf)
            self.config = \
                json.loads(json.dumps(configtree.as_plain_ordered_dict()))
        else:
            self.config = None
            
        self.transfer_register_file = transfer_register
        with open(transfer_register, 'r') as f:
            self.transfer_register = json.load(f)
            
        self.logger.info('Acquisition was configured with the following ' +
                         f'configuration: {pprint(self.config)}')
        self.logger.info('The transfer register contains the following ' +
                         f'information: {pprint(self.transfer_register)}')
    
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
        
    def get_recent_raw_file_names(self):
        self.queue_out.put((AcqMsgIDs.REQUEST_RAW_FILE_NAME, None))
        
    def get_last_raw_file(self, raw_file, target_dir):
        self.queue_out.put((AcqMsgIDs.REQUEST_LAST_RAW_FILE, (raw_file, target_dir)))
        
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

    def update_recent_raw_file_names(self, raw_file_names):
        with self.raw_file_names_lock:
            self.recent_raw_file_names = raw_file_names
    
    def received_recent_rawfile_names(self):
        raw_file_names_returned = False
        with self.raw_file_names_lock:
            if self.recent_raw_file_names != []:
                raw_file_names_returned = True
        return raw_file_names_returned
        
    def fetch_recent_raw_file_names(self):
        with self.raw_file_names_lock:
            recent_raw_file_names = self.recent_raw_file_names
            self.recent_raw_file_names = []
        return recent_raw_file_names
            
    def is_rawfile_downloaded(self):
        download_finished = False
        with self.raw_file_lock:
            raw_file_path = self.last_raw_file
            if self.last_raw_file != '':
                download_finished = True

        return download_finished
        
    def get_downloaded_raw_file_path(self):
        with self.raw_file_lock:
            raw_file_path = self.last_raw_file
            self.last_raw_file = ''
        return raw_file_path
        
    def update_raw_file_download_status(self, raw_file_path):
        with self.raw_file_lock:
            self.last_raw_file = raw_file_path
            
    def update_transfer_register(self, data):
        with self.transfer_register_lock:
            self.transfer_register.update(data)
            
    def save_transfer_register(self):
        with self.transfer_register_lock:
            with open(self.transfer_register_file, "w") as outfile:
                json.dump(self.transfer_register, outfile)
        
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
            elif AcqMsgIDs.RECEIVED_RAW_FILE_NAMES == cmd:
                self.update_recent_raw_file_names(payload)
            elif AcqMsgIDs.RAW_FILE_DOWNLOAD_FINISHED == cmd:
                self.update_raw_file_download_status(payload)
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
                        fconf,
                        transfer_register):
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
    
    acquisition.configure(fconf, transfer_register)
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
    acquisition.update_acquisition_status(AcqStatIDs.ACQUISITION_POST_ACQUISITION)
    acquisition.post_acquisition()
    acquisition.save_transfer_register()