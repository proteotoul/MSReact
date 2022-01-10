from acquisition_manager import AcquisitionManager

class MockAcquisitionManager(AcquisitionManager):
    
    def __init__(self):
        super().__init__()
        
    def interpret_acquisition(self, sequence, methods):
        self.sequence = sequence
        self.methods = methods
        self.num_acq = len(self.methods)