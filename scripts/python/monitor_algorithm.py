from algorithm import Algorithm

class MonitorAlgorithm(Algorithm):
    """
    Algorithm implementing simple monitoring

    ...

    Attributes
    ----------
    request_scan_cb : function
        WebSocket uri (universal resource identifier) to connect to
    rx_scan_format : dict
        The format in which the scans will be received from the Mass 
        Spectrometer instrument
    req_scan_format : dict
        The format in which a scan can be requested from the Mass 
        Spectrometer instrument
        
    Methods
    -------
    consume_scan(scan)
        Consumes a scan that was received from the Mass Spectrometer Instrument
    update_acq_meth(method):
        Updates the acquisition method 
    update_acq_seq(sequence):
        Updatest the acquisition sequence
    algorithm_body():
        The body of the algorithm that will be executed
    """

    """Cycle interval - TODO: This is only for mock."""
    CYCLE_INTERVAL = 10
    ALGORITHM_NAME = 'monitor'
    
    def __init__(self, request_scan_cb, rx_scan_format, req_scan_format):
        """
        Parameters
        ----------
        request_scan_cb : function
            WebSocket uri (universal resource identifier) to connect to
        rx_scan_format : dict
            The format in which the scans will be received from the Mass 
            Spectrometer instrument TODO - revise rx_scan_format
        req_scan_format : dict
            The format in which a scan can be requested from the Mass 
            Spectrometer instrument TODO - revise req_scan_format
        """
        self.request_scan_callback = request_scan_cb
        self.received_scan_format = rx_scan_format
        self.requested_scan_format = req_scan_format
        
    def update_acq_meth(self, method):
        """
        Parameters
        ----------
        method : Method
            Original acquisition method. The update_acq_meth function can
            overwrite the method if neccessary
        Returns
        -------
        Method: The updated acquisition method
        """
        return method
        
    def update_acq_seq(self, sequence):
        """
        Parameters
        ----------
        sequence : Sequence
            Original acquisition method. The update_acq_meth function can
            overwrite the method if neccessary
        Returns
        -------
        Sequence: The updated acquisition sequence
        """
        return sequence

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
   
