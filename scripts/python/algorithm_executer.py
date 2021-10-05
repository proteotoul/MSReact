import enum
import threading

class AlgorithmExecuter:
    """
    This module executes the algorithms

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
    
    def __init__(self, algorithm, method, sequence):
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
        self.algorithm_thread = 
            threading.Thread(target=self.algorithm.algorithm_body)
        self.method = method
        self.sequence = sequence
        
    def configure_algorithm(self):
        result = self.ConfigErrors.no_error
        success = self.algorithm.update_and_validate_acq_meth()
        if not success:
            result = self.ConfigErrors.method_error 
        else:
            success = self.algorithm.update_and_validate_acq_seq()
            if  not success:
                result = self.ConfigErrors.sequence_error
        return result
        
    def run_algorithm(self):
        self.algorithm.start()
        
    def stop_algorithm(self):
        self.algorithm.join()
        