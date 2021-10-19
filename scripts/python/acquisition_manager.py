class AcquisitionManager:
    
    DEFAULT_NUM_ACQUISITIONS = 1
    DEFAULT_METHODS = []
    
    def __init__(self):
        self.num_acq = self.DEFAULT_NUM_ACQUISITIONS
        
    def interpret_acquisition(self, sequence, methods):
        self.sequence = sequence
        self.methods = methods
        
    def get_next_method(self):
        method = None
        return method
        
    def check_acquisition_compatibility(self, algo_sequence, algo_methods):
        compatible = True
        return compatible