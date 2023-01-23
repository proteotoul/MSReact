from .. import acquisition_workflow as aw
from .ms_instrument import MassSpectrometerInstrument

class ThermoExplorisInstrument(MassSpectrometerInstrument):

    instrument_name = "Exploris"
    supported_acquisition_workflows = [aw.Listening,
                                       aw.Permanent,
                                       aw.LimitedByCount,
                                       aw.LimitedByDuration,
                                       aw.Method]
    
    def __init__(self):
        pass
        
    
