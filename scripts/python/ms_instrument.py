from acquisition_workflow import AcquisitionWorkflow

class MassSpectrometerInstrument:

    instrument_name = "BASE_MASS_SPECTROMETER_INSTRUMENT"
    supported_acquisition_workflows = [AcquisitionWorkflow]
    
    def __init__(self):
        pass
    
    def get_supported_acquisition_workflows(self):
        return self.supported_acquisition_workflows
        
    
        
        