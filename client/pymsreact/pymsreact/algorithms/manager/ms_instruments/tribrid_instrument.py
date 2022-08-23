from .. import acquisition_workflow as aw
from .ms_instrument import MassSpectrometerInstrument

class ThermoTribridInstrument(MassSpectrometerInstrument):

    instrument_name = "Tribrid"
    supported_acquisition_workflows = [aw.Listening,
                                       aw.Permanent,
                                       aw.LimitedByCount,
                                       aw.LimitedByDuration,
                                       aw.Method]
    
    def __init__(self):
        pass
        
    
