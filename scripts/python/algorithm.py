import enum
import threading

class Algorithm:
    '''
    An abstract class for algorithms

    ...

    Attributes
    ----------
    scan_request_action : function
        A function that the algorithm can call when it would like to request a 
        custom scan
    received_scan_format : dict
        The format in which the scans will be received from the Mass 
        Spectrometer instrument
    requested_scan_format : dict
        The format in which a scan can be requested from the Mass 
        Spectrometer instrument
    acquisition_method : Method
        The acquisition method to validate and update the default method to
    acquisition_sequence : Sequence
            The acquisition sequence to validate and update the default 
            sequence to
            
    Methods
    -------
    consume_scan(scan)
        Consumes a scan that was received from the Mass Spectrometer Instrument
    validate_methods_and_sequence(methods, sequence):
        Validates that the acquisition method(s) and sequence is appropriate
        for the algorithm and updates the algorithm's default method(s) and 
        sequence for that validated method(s) and sequences.
    algorithm_body():
        The body of the algorithm that will be executed
    '''

    '''Method - TODO: Create default method based on real method.'''
    ACQUISITION_METHOD = {}
    '''Sequence - List of Acquisitions'''
    ACQUISITION_SEQUENCE = []
    '''Cycle interval - TODO: This is only for mock.'''
    CYCLE_INTERVAL = 10
    '''Name of the algorithm. This is a mandatory field for the algorithms'''
    ALGORITHM_NAME = 'abstract_algorithm'
    '''Level of MS scans that are transferred from the mock server.
       eg. - 1 means only MS scans are transferred from the mock server. 
           - 2 means MS and MS2 scans are transferred from the mock server
       Note - In case of custom scan requests the requested scan will be 
              transferred from the mock server not regarding the scan level,
              if it's available in the raw file.'''
    TRANSMITTED_SCAN_LEVEL = [1, 2]
    
    class AcquisitionStatus(enum.Enum):
        scan_available          = 0
        scan_not_available      = 1
        acquisition_finished    = 2
    
    def __init__(self):
        self.acquisition_method = self.ACQUISITION_METHOD
        self.acquisition_sequence = self.ACQUISITION_SEQUENCE
        self.current_acquisition = None
        
    def configure_algorithm(self, 
                            runner_cb,
                            command_ids):
        """
        Parameters
        ----------
        scan_req_act : function
            A function that the algorithm can call when it would like to 
            request a custom scan
        """
        #self.fetch_received_scan = fetch_received_scan
        #self.request_scan = request_scan
        #self.start_acquisition = start_acquisition
        #self.finish_algo = finish_algo
        self.runner_cb = runner_cb
        self.command_ids = command_ids
        
    def set_current_acquisition(self, acquisition):
        self.current_acquisition = acquisition
        
    def fetch_received_scan(self):
        return self.runner_cb(self.command_ids.FETCH_RECEIVED_SCAN, None)
        
    def request_custom_scan(self, request):
        self.runner_cb(self.command_ids.REQUEST_SCAN, request)
        
    def request_repeating_scan(self, request):
        self.runner_cb(self.command_ids.REQUEST_REPEATING_SCAN, request)
        
    def cancel_repeating_scan(self, request):
        self.runner_cb(self.command_ids.CANCEL_REPEATING_SCAN, request)
        
    def signal_error_to_runner(self, error_msg):
        self.runner_cb(self.command_ids.ERROR, error_msg)
        
    def is_acquisition_ended(self):
        return self.current_acquisition.acquisition_finished.is_set()
        
    def validate_methods_and_sequence(self, methods, sequence):
        """
        Parameters
        ----------
        method : Method
            The acquisition method to validate and update the default method to
        sequence : Sequence
            The acquisition sequence to validate and update the default 
            sequence to
        Returns
        -------
        Bool: True if the update and validation of the acquisition method and 
              sequence was successful and False if it failed
        """
        success = True
        self.acquisition_method = method
        self.acquisition_sequence = sequence
        return success
        
    def validate_scan_formats(self, rx_scan_format, req_scan_format):
        """
        Parameters
        ----------
        rx_scan_format : Dict
            The acquisition method to validate and update the default method to
        req_scan_format : Dict
            The acquisition sequence to validate and update the default 
            sequence to
        Returns
        -------
        Bool: True if the update and validation of the received scan format and 
              the requested scan format was successful and False if it failed
        """
        success = True
        self.received_scan_format = rx_scan_format
        self.requested_scan_format = req_scan_format
        return success
        
    def algorithm_body(self):
        pass