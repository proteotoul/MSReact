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
    """
    Base class for acquisition workflows, aiming to ease the work with different
    acquisition workflows provided by vendors.

    ...

    Attributes
    ----------
    is_supported : bool
       Decides whether this acquisition workflow is supported or not.
    parameter : 
       The parameter of the acquisition, depends on the actual acquisition.
    
    """

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
        """Sets the parameter of the acquisition.
        
        Parameters
        ----------
        parameter :
            The parameter of the acquisition, depends on the actual acquisition.
        """
        if self.validate_parameter(parameter):
            self.parameter = parameter
        else:
            pass
            
    def set_support(self, is_supported):
        """Sets wether this type of acquisition workflow is supported or not.
        
        Parameters
        ----------
        is_supported :
            Decides whether this acquisition workflow is supported or not.
        """
        self.is_supported = is_supported
    
    def validate_parameter(self, parameter):
        """Validates whether the given parameter is meeting the requirements 
           of the acquisition workflow parameter.
        
        Parameters
        ----------
        parameter :
            The parameter to validate against the requirements.
            
        Returns:
            bool: True if the given parameter passes the validation, false if not
        """
        return True
        
    def get_acquisition_workflow_representation(self):
        """Returns the vendor conform representation of the acquisition workflow

        Returns:
            dict: String - string dictionary containing the AcquisitionType and
                  AcquisitionParam.
        """
        return {"AcquisitionType" : str(self.type_id),
                "AcquisitionParam" : str(self.parameter)}
        
class Listening(AcquisitionWorkflow):
    """
    Listening workflow class. Listening workflow does not trigger new 
    acquisition, just listens to incoming scans and can request custom scans.
    """
    name = "listening"
    type_id = 1
    is_acquisition_triggering = False
        
class Permanent(AcquisitionWorkflow):
    """
    Permanent workflow class. Permanent workflow triggers a new acquisition,
    listens to scans and can request custom scans. The acquisition will only
    stop on request.
    """
    name = "permanent"
    type_id = 2
        
class LimitedByCount(AcquisitionWorkflow):
    """
    LimitedByCount workflow class. LimitedByCount workflow triggers a new 
    acquisition, listens to scans and can request custom scans. The length of 
    the acquisition is limited by the count parameter that is the amount of 
    scans to be taken by the instrument before stopping the acquisition.
    """
    name = "limited by count"
    type_id = 3
    parameter_types = int
    
    def validate_parameter(self, parameter):
        """Validates whether the given parameter is an integer
        
        Parameters
        ----------
        parameter :
            The parameter to validate against the requirement.
            
        Returns:
            bool: True if the given parameter is an integer otherwise False
        """
        return isinstance(parameter, self.parameter_types)
        
class LimitedByDuration(AcquisitionWorkflow):
    """
    LimitedByDuration workflow class. LimitedByDuration workflow triggers a new 
    acquisition, listens to scans and can request custom scans. The length of 
    the acquisition is limited by the time parameter that is the amount of 
    time (in seconds) to pass before stopping the acquisition.
    """
    name = "limited by duration"
    type_id = 4
    parameter_types = (int, float)
    
    def validate_parameter(self, parameter):
        """Validates whether the given parameter is an integer or float type
        
        Parameters
        ----------
        parameter :
            The parameter to validate against the requirements.
            
        Returns:
            bool: True if the given parameter is an integer or float otherwise 
                  False
        """
        return (isinstance(parameter, self.parameter_types))
        
class Method(AcquisitionWorkflow):
    """
    Method workflow class. Method workflow triggers a new acquisition, listens 
    to scans and can request custom scans. The acquisition is determined by the
    parameter that is a method file (the location and name of the method file).
    """
    name = "method"
    type_id = 5
    method_extension = ".meth"
    parameter_types = str
    
    def validate_parameter(self, parameter):
        """Validates whether the given parameter represents a method file. It
           has to be a string and the file has to have a .meth extension.
        
        Parameters
        ----------
        parameter :
            The parameter to validate against the requirements.
            
        Returns:
            bool: True if the given parameter represents a method file otherwise
                  False.
        """
        return (isinstance(parameter, self.parameter_types) and 
                self.method_extension == Path(parameter).suffix)