import algorithm_run_modes

class ThermoTribidInstrument(MassSpectrometerInstrument):

    instrument_name = "Tribid"
    supported_acquisition_workflows = [Listening,
                                       Permanent,
                                       LimitedByCount,
                                       LimitedByDuration,
                                       Method]
    
    def __init__(self):
        pass
        
    
