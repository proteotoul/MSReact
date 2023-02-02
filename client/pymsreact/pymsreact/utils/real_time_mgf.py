import threading
import queue
import logging
import time
from algorithms.manager.acquisition import ScanFields as sf
from algorithms.manager.acquisition import CentroidFields as cf

class RealTimeMGFWriter:
    
    BUF_LEN = 30 # Number of scans to store in the buffer
    WRITE_RATE = 3 # Per minute rate of writing to file
       
    def __init__(self, file_path, buffer = BUF_LEN, rate = WRITE_RATE):
        self._file_path = file_path
        self._file_object = None
        self._scan_buffer = queue.Queue(buffer * rate)
        self._mgf_string = ""
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._scan_count = 0
        self._logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self._file_object = open(self._file_path, 'w')
        self._worker_thread = threading.Thread(target = self._write_worker)
        self._worker_thread.start()
        return self
    
    def __exit__(self, exc_type, exc_value, tb):
        self._stop_event.set()
        self._worker_thread.join()
        self._file_object.flush()
        self._file_object.close()
    
    def write_scan(self, scan):
        try:
            self._scan_buffer.put(scan, block=False)
        except queue.Full:
            self._logger.info("MGFWriter buffer is full, rate of receiving "
                              + "scans is higher than rate of processing.")
        
    def _convert_scan(self, scan):
        scan_head = "BEGIN IONS\n" + \
                    f"TITLE=controllerType={0} " + \
                    f"controllerNumber={1} " + \
                    f"scan={scan[sf.SCAN_NUMBER]}\n" + \
                    f"SCANS={scan[sf.SCAN_NUMBER]}\n" + \
                    f"RTINSECONDS={60 * scan[sf.RETENTION_TIME]}\n" + \
                    f"PEPMASS={scan[sf.PRECURSOR_MASS]}\n"
                    
        spectra = "".join(f"{round(c[cf.MZ], 5)} {round(c[cf.INTENSITY], 3)}\n"
                          for c in scan[sf.CENTROIDS])
                    
        scan_tail = "END IONS\n\n"
        
        return scan_head + spectra + scan_tail
    
    def _write_to_file(self):
        self._logger.info("Written to file")
        self._file_object.write(self._mgf_string)
        self._scan_count = 0
        self._mgf_string = ""
        
    def _write_worker(self):
        self._logger.info("MGF writer starting...")
        while True:
            try:
                scan = self._scan_buffer.get_nowait()
                self._mgf_string = self._mgf_string + self._convert_scan(scan)
                self._scan_count = self._scan_count + 1
                if self._scan_count >= self.BUF_LEN:
                    self._write_to_file()
            except queue.Empty:
                pass
            
            if self._stop_event.is_set():
                self._write_to_file()
                break
            else:
                time.sleep(0.025)
        
        
if __name__ == "__main__":
    pass