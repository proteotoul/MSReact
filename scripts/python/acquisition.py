from ms_instrument import MassSpectrometerInstrument
import acquisition_workflow as aw
DEFAULT_NAME = "Default Acquisition"

class Acquisition:
    def __init__(self,
                 name = DEFAULT_NAME,
                 instrument = MassSpectrometerInstrument(),
                 acquisition_workflow = aw.AcquisitionWorkflow(),
                 pre_acquisition = None,
                 intra_acquisition = None,
                 post_acquisition = None):
        self.name = "Default Acquisition"
        self.instrument = instrument
        if acquisition_workflow.__class__ in self.instrument.supported_acquisition_workflows:
            self.acquisition_workflow = acquisition_workflow
        else:
            raise ValueError('Acquisition workflow ' +
                             f'{acquisition_workflow.__name__} is not supported for ' +
                             f'{self.instrument.instrument_name} instrument.')
        self.pre_acquisition = \
            self.default_action if pre_acquisition is None else pre_acquisition
        self.intra_acquisition = \
            self.default_action if intra_acquisition is None else intra_acquisition
        self.post_acquisition = \
            self.default_action if post_acquisition is None else post_acquisition
        
    def default_action(self):
        pass
        
if __name__ == "__main__":
    acq = Acquisition(acquisition_workflow = aw.Listening)
    print(acq.name)