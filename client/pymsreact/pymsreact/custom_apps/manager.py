import importlib
import inspect
import os
import pkgutil
from .app import CustomApp

class CustomAppManager:
    CUSTOM_APPS = []
    def __init__(self):
        self.discover_apps()       
            
    def get_app_names(self):
        return [CustomApp.APP_NAME for CustomApp in self.CUSTOM_APPS]
        
    def find_by_name(self, name):
        found_app = False
        for i in range(len(self.CUSTOM_APPS)):
            if name == self.CUSTOM_APPS[i].APP_NAME:
                found_app = True
                return self.CUSTOM_APPS[i]
        if not found_app:
            return None
            
    def discover_apps(self):
        current_dir = os.getcwd() + '\\custom_apps'
        module_infos = pkgutil.iter_modules([current_dir])
        for info in module_infos:
            import_name = 'custom_apps.' + info.name
            module = importlib.import_module(import_name)
            for member in inspect.getmembers(module):
                if (inspect.isclass(member[1]) and 
                    issubclass(member[1], CustomApp) and
                    member[1] is not CustomApp):
                    self.CUSTOM_APPS.append(member[1])