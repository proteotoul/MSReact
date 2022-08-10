from . import acquisition_workflow as aw

DEFAULT_ACQUISITION_WORKFLOW = aw.Listening
DEFAULT_ACQUISITION_PARAMETER = None
DEFAULT_SINGLE_PROCESSING_DELAY = 0
DEFAULT_WAIT_FOR_CONTACT_CLOSURE = False
DEFAULT_RAW_FILE_NAME = "Deafault.RAW"
DEFAULT_SAMPLE_NAME = "-"
DEFAULT_COMMENT = "-"

class AcquisitionSettings:
    def __init__(self):
        # Set default settings
        self.update_settings()
        
    def update_settings(self,
                        workflow = DEFAULT_ACQUISITION_WORKFLOW,
                        workflow_param = DEFAULT_ACQUISITION_PARAMETER,
                        single_processing_delay = DEFAULT_SINGLE_PROCESSING_DELAY,
                        wait_for_contact_closure = DEFAULT_WAIT_FOR_CONTACT_CLOSURE,
                        raw_file_name = DEFAULT_RAW_FILE_NAME,
                        sample_name = DEFAULT_SAMPLE_NAME,
                        comment = DEFAULT_COMMENT):
                                  
        self.acquisition_workflow = workflow()
        self.acquisition_workflow.set_parameter(workflow_param)
        self.single_processing_delay = single_processing_delay
        self.wait_for_contact_closure = wait_for_contact_closure
        self.acquisition_raw_file_name = raw_file_name
        self.sample_name = sample_name
        self.acquisition_comment = comment
        
    def get_settings_dict(self):
        return {"AcquisitionType" : str(self.acquisition_workflow.type_id),
                "AcquisitionParam" : str(self.acquisition_workflow.parameter),
                "RawFileName" : self.acquisition_raw_file_name,
                "SampleName" : self.sample_name,
                "Comment" : self.acquisition_comment,
                "SingleProcessingDelay" : str(self.single_processing_delay),
                "WaitForContactClosure" : str(self.wait_for_contact_closure)}