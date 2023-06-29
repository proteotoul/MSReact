import logging
import time
import os
import subprocess
from subprocess import Popen, CREATE_NEW_CONSOLE
from contextlib import contextmanager

@contextmanager
def environ(**env):
    originals = {k: os.environ.get(k) for k in env}
    for k, val in env.items():
        if val is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = val
    try:
        yield
    finally:
        for k, val in originals.items():
            if val is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = val

class FileConverters:
    '''
    This module contains python wrappers for file converter executables, such as
    thermo2mzdb, tdf2mzdb and mzdb2mgf.
    '''
    MZDBTOOLS_PATH = '.\\tools\\mzdbtools_0.4.5_windows_x64'
    MZDBTOOLS_EXECUTABLE = '\\mzdbtools.exe'
    MZDBTOOLS_LIB = '\\lib'
    THERMO_TO_MZDB_COMMAND = 'thermo2mzdb'
    TDF_TO_MZDB_COMMAND = 'tdf2mzdb'
    MZDB_TO_MGF_COMMAND = 'mzdb2mgf'

    def __init__(self):
        pass  

    def thermo_to_mzdb(self, args):
        """Python wrapper for raw2mzdb converter."""
        self._init_mzdb_tools()
        converter = [self.mzdbtools_exe_path] + [self.THERMO_TO_MZDB_COMMAND]
        args_list = self._pack_args(args)
        with environ(PATH=self.updated_path):
            self._run_in_process(converter, args_list)
        
    def tdf_to_mzdb(self, args):
        """Python wrapper for tdf2mzdb converter."""
        self._init_mzdb_tools()
        converter = [self.mzdbtools_exe_path] + [self.TDF_TO_MZDB_COMMAND]
        args_list = self._pack_args(args)
        with environ(PATH=self.updated_path):
            self._run_in_process(converter, args_list)
        
    def mzdb_to_mgf(self, args):
        """Python wrapper for mzdb2mgf converter."""
        self._init_mzdb_tools()
        converter = [self.mzdbtools_exe_path] + [self.MZDB_TO_MGF_COMMAND]
        args_list = self._pack_args(args)
        with environ(PATH=self.updated_path):
            self._run_in_process(converter, args_list)
        
    def _init_mzdb_tools(self):
        self.mzdbtools_exe_path = \
            self.MZDBTOOLS_PATH + self.MZDBTOOLS_EXECUTABLE
        self.mzdbtools_lib_path = \
            self.MZDBTOOLS_PATH + self.MZDBTOOLS_LIB
        self.updated_path = \
            os.environ.get('PATH') + ';' + self.mzdbtools_lib_path
            
    def _pack_args(self, args):
        args_list = []
        for i in args:
            args_list = args_list + [i] + [args[i]]
        return args_list
        
    def _run_in_process(self, converter, args):
        msg = converter + args
        self.proc = Popen(msg, creationflags=CREATE_NEW_CONSOLE)

        
if __name__ == "__main__":
    file_converters = FileConverters()
    args_thermo_to_mzdb = \
        {"-i" : "D:\\analysis\\Exploris\\2023_05_09\\OXZUD230509_03.raw",
         "-o" : "OXZUD230509_03.raw.mzDB"}
    #file_converters.thermo_to_mzdb(args_thermo_to_mzdb)
    args_mzdb_to_mgf = \
        {"-i" : "OXZUD230509_03.raw.mzDB",
         "-o" : "OXZUD230509_03.raw.mzDB.mgf"}
    file_converters.mzdb_to_mgf(args_mzdb_to_mgf)
    