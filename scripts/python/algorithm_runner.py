import enum
import threading

class AlgorithmRunner:
    """
    This module runs the algorithms

    ...

    Attributes
    ----------
    algorithm : Algorithm
        The algorithm that needs to be executed
    method: Dict
        The acquisition method
    sequence: Dict
        The acquisition sequence
        
    Methods
    -------
    configure_algorithm:
        Configures the algorithm
    run_algorithm:
        Starts running the algorithm
    stop_algorithm:
        Stops running the algorithm
    """

    """Default cycle interval - TODO: This is only for mock."""
    DEFAULT_CYCLE_INTERVAL = 10
    
    class ConfigErrors(enum.Enum):
        no_error        = 0
        method_error    = 1
        sequence_error  = 2
    
    def __init__(self, algorithm, method, sequence, scan_req_act):
        """
        Parameters
        ----------
        algorithm : ALGORITHM
            Algorithm to execute by algorithm executer
        rx_scan_format : dict
            The format in which the scans will be received from the Mass 
            Spectrometer instrument
        req_scan_format : dict
            The format in which a scan can be requested from the Mass 
            Spectrometer instrument
        """
        self.algorithm = algorithm
        self.method = method
        self.sequence = sequence
        self.req_scan_act = req_scan_act
        
        self.algorithm_thread = 
            threading.Thread(target=self.algorithm.algorithm_body)
        
    def configure_algorithm(self, methods, sequence):
        set_scan_request_action(self.scan_request_action)
        success = \ 
            self.algorithm.validate_scan_formats()
        success = \
            self.algorithm.validate_methods_and_sequence(methods, sequence)
        return success
        
    def run_algorithm(self):
        self.algorithm_thread.start()
        
    def stop_algorithm(self):
        self.algorithm.join()
        
    def scan_request_action(self, request):
        self.scan_req_act(request)
        