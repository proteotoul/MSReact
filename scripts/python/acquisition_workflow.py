from pathlib import Path

class AcquisitionWorkflows:
    def __init__(self, supported_workflows):
        self.supported_workflows = supported_workflows
        
    def get_available_names(self):
        return [AcquisitionWorkflow.name for AcquisitionWorkflow 
                in self.supported_workflows]
        
    def find_by_name(self, name):
        workflow = None
        for i in range(len(self.supported_workflows)):
            if name == self.supported_workflows[i].name:
                workflow = self.supported_workflows[i]
                break
        return workflow

class AcquisitionWorkflow:
    name = "base acquisition workflow"
    type_id = -1
    is_supported = False
    is_acquisition_triggering = True
    parameter = None
    parameter_types = None
    
    def __init__(self, is_supported = False, parameter = None):
        self.is_supported = is_supported
        if ((parameter is None) or self.validate_parameter(parameter)):
            self.parameter = parameter
        else:
            raise ValueError('The provided acquisition parameter ' +
                             f'[{parameter}] is not a valid parameter for ' +
                             f'{self.__class__.__name__} workflow.')
        
    def set_parameter(self, parameter):
        if self.validate_parameter(parameter):
            self.parameter = parameter
        else:
            pass
            
    def set_support(self, is_supported):
        self.is_supported = is_supported
    
    def validate_parameter(self, parameter):
        return True
        
    def get_acquisition_workflow_representation(self):
        return {"AcquisitionType" : str(self.type_id),
                "AcquisitionParam" : str(self.parameter)}
        
class Listening(AcquisitionWorkflow):
    name = "listening"
    type_id = 1
    is_acquisition_triggering = False
        
class Permanent(AcquisitionWorkflow):
    name = "permanent"
    type_id = 2
        
class LimitedByCount(AcquisitionWorkflow):
    name = "limited by count"
    type_id = 3
    parameter_types = int
    
    def validate_parameter(self, parameter):
        return isinstance(parameter, self.parameter_types)
        
class LimitedByDuration(AcquisitionWorkflow):
    name = "limited by duration"
    type_id = 4
    parameter_types = (int, float)
    
    def validate_parameter(self, parameter):
        return (isinstance(parameter, self.parameter_types))
        
class Method(AcquisitionWorkflow):
    name = "method"
    type_id = 5
    method_extension = ".meth"
    parameter_types = str
    
    def validate_parameter(self, parameter):
        return (isinstance(parameter, self.parameter_types) and 
                self.method_extension == Path(parameter).suffix)
        
if __name__ == "__main__":
    my_count_limited_acq = LimitedByCount()
    print(my_count_limited_acq.validate_parameter(90))
    my_duration_limited_acq = LimitedByDuration()
    print(my_duration_limited_acq.validate_parameter(90.1))
    my_method_acq = Method()
    print(my_method_acq.validate_parameter("sanyi.meth"))