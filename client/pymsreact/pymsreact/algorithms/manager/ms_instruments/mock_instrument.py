from .. import acquisition_workflow as aw
from .ms_instrument import MassSpectrometerInstrument

class MockInstrument(MassSpectrometerInstrument):

    instrument_name = "Mock"
    supported_acquisition_workflows = [aw.Listening]
    
    def __init__(self):
        pass