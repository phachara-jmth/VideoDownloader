# First, update class_terminalLogger.py to maintain last 10 lines
import sys
import os
import datetime
from collections import deque

class TerminalLogger:
    def __init__(self):
        self.log_dir = "./Log"
        os.makedirs(self.log_dir, exist_ok=True)  # Ensure the log directory exists
        self.current_date = datetime.datetime.now().strftime("%y%m%d")
        self.log_file = self._get_log_file()
        self.original_stdout = sys.stdout
        sys.stdout = self  # Redirect stdout to this class
        
        # Store recent logs in a deque with max length of 10
        self.recent_logs = deque(maxlen=10)
        
        # List of callback functions to notify when logs are updated
        self.log_update_callbacks = []
    
    def _get_log_file(self):
        return open(os.path.join(self.log_dir, f"log_{self.current_date}.txt"), "a", encoding="utf-8")
    
    def write(self, message):
        if message.strip():  # Ignore empty messages
            now = datetime.datetime.now()
            timestamp = now.strftime('%Y-%m-%d, %H:%M:%S')
            log_entry = f"{timestamp}: {message}\n\n"
            
            # Check if date changed
            new_date = now.strftime("%y%m%d")
            if new_date != self.current_date:
                self.log_file.close()
                self.current_date = new_date
                self.log_file = self._get_log_file()
            
            self.log_file.write(log_entry)
            self.log_file.flush()
            
            # Add to recent logs
            self.recent_logs.append(f"{timestamp}: {message}")
            
            # Notify all registered callbacks
            for callback in self.log_update_callbacks:
                callback(self.get_recent_logs())
        
        self.original_stdout.write(message)
    
    def get_recent_logs(self):
        return list(self.recent_logs)
    
    def get_last_log(self):
        return self.recent_logs[-1] if self.recent_logs else None
        
    def register_update_callback(self, callback):
        """Register a callback function to be called when logs are updated"""
        if callback not in self.log_update_callbacks:
            self.log_update_callbacks.append(callback)
    
    def flush(self):
        self.log_file.flush()
        self.original_stdout.flush()
    
    def close(self):
        sys.stdout = self.original_stdout  # Restore stdout
        self.log_file.close()