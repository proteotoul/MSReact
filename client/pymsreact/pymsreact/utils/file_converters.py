import logging
import time
import os
import subprocess
from subprocess import Popen, PIPE, STDOUT, CREATE_NEW_CONSOLE
from contextlib import contextmanager
from .temp_environ import temp_environ

class FileConverters:
    '''
    This module contains python wrappers for file converter executables, such as
    thermo2mzdb, tdf2mzdb and mzdb2mgf.
    '''
    MZDBTOOLS_PATH = '\\tools\\mzdbtools_0.4.5_windows_x64'
    MZDBTOOLS_EXECUTABLE = '\\mzdbtools.exe'
    MZDBTOOLS_LIB = '\\lib'
    THERMO_TO_MZDB_COMMAND = 'thermo2mzdb'
    TDF_TO_MZDB_COMMAND = 'tdf2mzdb'
    MZDB_TO_MGF_COMMAND = 'mzdb2mgf'
    NO_ERROR = 0

    def __init__(self):
        self.logger = logging.getLogger(__name__) 

    def thermo_to_mzdb(self, args):
        """Python wrapper for raw2mzdb converter."""
        self._init_mzdb_tools()
        converter = [self.mzdbtools_exe_path] + [self.THERMO_TO_MZDB_COMMAND]
        args_list = self._pack_args(args)
        result = 0
        with temp_environ(PATH=self.updated_path):
            result = self._run_in_process(converter, args_list)
        return result == self.NO_ERROR
        
    def tdf_to_mzdb(self, args):
        """Python wrapper for tdf2mzdb converter."""
        self._init_mzdb_tools()
        converter = [self.mzdbtools_exe_path] + [self.TDF_TO_MZDB_COMMAND]
        args_list = self._pack_args(args)
        result = 0
        with temp_environ(PATH=self.updated_path):
            result = self._run_in_process(converter, args_list)
        return result == self.NO_ERROR
        
    def mzdb_to_mgf(self, args):
        """Python wrapper for mzdb2mgf converter."""
        self._init_mzdb_tools()
        converter = [self.mzdbtools_exe_path] + [self.MZDB_TO_MGF_COMMAND]
        args_list = self._pack_args(args)
        result = 0
        with temp_environ(PATH=self.updated_path):
            result = self._run_in_process(converter, args_list)
        return result == self.NO_ERROR
        
    def _init_mzdb_tools(self):
        self.mzdbtools_exe_path = \
            '.' + self.MZDBTOOLS_PATH + self.MZDBTOOLS_EXECUTABLE
        self.mzdbtools_lib_path = \
            self.MZDBTOOLS_PATH + self.MZDBTOOLS_LIB
        self.updated_path = \
            os.environ.get('PATH') + ';' + os.getcwd() + self.mzdbtools_lib_path
            
    def _pack_args(self, args):
        args_list = []
        for i in args:
            args_list = args_list + [i] + [args[i]]
        return args_list
        
    def _run_in_process(self, converter, args):
        msg = converter + args
        self.proc = Popen(msg,
                          stdout=PIPE, 
                          stderr=STDOUT)
        with self.proc.stdout:
            self._log_subprocess_output(self.proc.stdout)
        return self.proc.wait()
        
    def _log_subprocess_output(self, pipe):
        for line in iter(pipe.readline, b''): # b'\n'-separated lines
            self.logger.info(line.decode("utf-8"))
        
if __name__ == "__main__":

    FORMAT = '%(message)s'
    logging.basicConfig(format=FORMAT, level=20)
    file_converters = FileConverters()
    args_thermo_to_mzdb = \
        {"-i" : "D:\\data\\OFCCF2300322_10.raw",
         "-o" : "OFCCF2300322_10.raw.mzDB"}
    file_converters.thermo_to_mzdb(args_thermo_to_mzdb)
    args_mzdb_to_mgf = \
        {"-i" : "OFCCF2300322_10.raw.mzDB",
         "-o" : "OFCCF2300322_10.raw.mzDB.mgf"}
    file_converters.mzdb_to_mgf(args_mzdb_to_mgf)
    