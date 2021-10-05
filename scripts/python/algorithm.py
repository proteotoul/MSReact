class Algorithm:
    """
    An abstract class for algorithms

    ...

    Attributes
    ----------
    request_scan_callback : function
        WebSocket uri (universal resource identifier) to connect to
    received_scan_format : dict
        The format in which the scans will be received from the Mass 
        Spectrometer instrument
    requested_scan_format : dict
        The format in which a scan can be requested from the Mass 
        Spectrometer instrument
        
    Methods
    -------
    consume_scan(scan)
        Consumes a scan that was received from the Mass Spectrometer Instrument
    update_and_validate_acq_meth(method):
        Updates and validates the acquisition method 
    update_and_validate_acq_seq(sequence):
        Updatest and validates the acquisition sequence
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
    ALGORITHM_NAME = 'abstract_algorithm'
    
    def __init__(self, request_scan_cb, rx_scan_format, req_scan_format):
        """
        Parameters
        ----------
        request_scan_cb : function
            WebSocket uri (universal resource identifier) to connect to
        rx_scan_format : dict
            The format in which the scans will be received from the Mass 
            Spectrometer instrument
        req_scan_format : dict
            The format in which a scan can be requested from the Mass 
            Spectrometer instrument
        acquisition_method: dict
            Acquisition method to use for mass spectrometer acqusition
        acquisition_sequence: dict
            Acquisition sequence to use for mass spectrometer acquisitions
        """
        self.request_scan_callback = request_scan_cb
        self.received_scan_format = rx_scan_format
        self.requested_scan_format = req_scan_format
        self.acquisition_method = DEFAULT_ACQUISITION_METHOD
        self.acquisition_sequence = DEFAULT_ACQUISITION_SEQUENCE
        
    def update_and_validate_acq_meth(self, method):
        """
        Parameters
        ----------
        method : Method
            The method to validate and update the default method to
        Returns
        -------
        Bool: True if the update and validation of the acquisition method was
              successful and False if it failed
        """
        self.acquisition_method = method
        success = True
        return success
        
    def update_and_validate_acq_seq(self, sequence):
        """
        Parameters
        ----------
        sequence : Sequence
            Original acquisition method. The update_acq_meth function can
            overwrite the method if neccessary
        Returns
        -------
        Bool: True if the update and validation of the acquisition sequence was 
              successful and False if it failed
        """
        self.acquisition_sequence = sequence
        success = True
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
        pass