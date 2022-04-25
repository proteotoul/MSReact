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
        