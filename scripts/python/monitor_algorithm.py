from algorithm import Algorithm

class MonitorAlgorithm(Algorithm):
    """
    Algorithm implementing simple monitoring

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
    """

    """Method - TODO: Create default method based on real method."""
    ACQUISITION_METHOD = {}   
    """Sequence - TODO: Create default method based on real method."""
    ACQUISITION_SEQUENCE = {}
    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    """Name of the algorithm. This is a mandatory field for the algorithms"""
    ALGORITHM_NAME = 'monitor'
    
    def __init__(self):
        self.acquisition_method = DEFAULT_ACQUISITION_METHOD
        self.acquisition_sequence = DEFAULT_ACQUISITION_SEQUENCE
        
    def set_scan_request_action(self, scan_req_act):
        """
        Parameters
        ----------
        scan_req_act : function
            A function that the algorithm can call when it would like to 
            request a custom scan
        """
        self.scan_request_action = scan_req_act
        
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
        
    def consume_scan(self, scan):
        """
        Parameters
        ----------
        scan : dict
            Scan received from the Mass Spectrometer Instrument
        """
        pass
        
    def algorithm_body(self):
        while True:
            pass