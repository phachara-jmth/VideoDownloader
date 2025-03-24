import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QLineEdit, QHBoxLayout, QVBoxLayout, QWidget, 
                             QFileDialog, QSystemTrayIcon, QMenu, QTextEdit)
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QObject, Slot
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QStyle  # Import QStyle explicitly
from class_downloader import Downloader
from class_terminalLogger import TerminalLogger
from queue import Queue
from time import sleep
import threading
import datetime

# Signal class for thread-safe communication with the UI
class WorkerSignals(QObject):
    # Define signals to communicate with the main thread
    log_message = Signal(str)
    download_started = Signal(str)
    download_complete = Signal(str)
    download_error = Signal(str, str)

class logDisplayData():
    def __init__(self):
        self.lines = []

    def add_line(self, line):
        self.lines.append(f'{datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")}:\n\t{line}\n')
        if len(self.lines) > 10:
            self.lines.pop(0)
    def get_lines(self):
        return self.lines
    
class MainWindow(QMainWindow):
    def __init__(self, logger):
        super().__init__()
        
        self._downloader = Downloader()
        self.logger = logger
        self.log_display_data = logDisplayData()
        # Setup signals for thread-safe communication
        self.worker_signals = WorkerSignals()
        self.worker_signals.log_message.connect(self.handle_log_message)
        self.worker_signals.download_started.connect(self.handle_download_started)
        self.worker_signals.download_complete.connect(self.handle_download_complete)
        self.worker_signals.download_error.connect(self.handle_download_error)
        
        # Setup download queue and worker thread
        self.queue_download = Queue()
        self._running = True
        self.thread_handle_download_queue = threading.Thread(target=self.run_handle_download_queue)
        self.thread_handle_download_queue.daemon = True
        
        self.setWindowTitle("Video Downloader")
        self.setMinimumSize(600, 400)
        
        # Create config file if it doesn't exist
        self.config_file = "config.json"
        if not os.path.exists(self.config_file):
            with open(self.config_file, "w") as f:
                json.dump({"targetPath": ""}, f)
        
        # Load config
        with open(self.config_file, "r") as f:
            self.config = json.load(f)
        
        # Set up the UI
        self.setup_ui()
        
        # Register for log updates
        #self.logger.register_update_callback(self.update_log_display)
        
        # Start the download thread after UI is set up
        self.thread_handle_download_queue.start()
        #self.safe_log_message("Download queue worker thread started!")

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Path selection row
        path_layout = QHBoxLayout()
        
        self.path_label = QLabel("Download Path:")
        path_layout.addWidget(self.path_label)
        
        self.path_display = QLabel(self.config.get("targetPath", ""))
        self.path_display.setStyleSheet("background-color: #f0f0f0; color: black; padding: 8px; border-radius: 4px;")
        path_layout.addWidget(self.path_display, 1)  # 1 is stretch factor
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.select_folder)
        path_layout.addWidget(self.browse_button)
        
        main_layout.addLayout(path_layout)
        
        # Line edit row
        input_layout = QHBoxLayout()
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Enter or paste URL here")
        # Make Enter key trigger the download
        self.line_edit.returnPressed.connect(self.run_function)
        input_layout.addWidget(self.line_edit, 1)  # 1 is stretch factor
        
        self.run_button = QPushButton("Download")
        self.run_button.clicked.connect(self.run_function)
        input_layout.addWidget(self.run_button)
        
        main_layout.addLayout(input_layout)
        
        # Add queue status
        self.queue_status = QLabel("Ready to download")
        self.queue_status.setStyleSheet("color: #333; font-size: 10pt;")
        main_layout.addWidget(self.queue_status)
        
        # Add Log Display
        log_layout = QVBoxLayout()
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Log Output (Last 10 Lines):"))
        
        # Add clear log button
        clear_log_button = QPushButton("Clear")
        clear_log_button.setMaximumWidth(80)
        clear_log_button.clicked.connect(self.clear_log_display)
        log_header.addWidget(clear_log_button)
        
        log_layout.addLayout(log_header)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #f5f5f5; color: #333; font-family: monospace;")
        self.log_display.setMinimumHeight(200)
        log_layout.addWidget(self.log_display)
        
        main_layout.addLayout(log_layout)
        
        # Initialize log display with any existing logs
        #self.update_log_display(self.logger.get_recent_logs())
        
        # Add a timer to update the queue status
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second

    def update_status(self):
        """Update the queue status display"""
        queue_size = self.queue_download.qsize()
        if queue_size == 0:
            self.queue_status.setText("Ready to download")
        else:
            self.queue_status.setText(f"Downloads in queue: {queue_size}")
        last_log = self.logger.get_last_log()
        
        if last_log == None:
            return
        
        if '[download]' in last_log and '%' in last_log:
            last_log = last_log.split('[download]')[1]
            self.worker_signals.log_message.emit(last_log)
    
    def clear_log_display(self):
        """Clear the log display"""
        self.log_display.clear()
        self.safe_log_message("Log display cleared by user")
    
    def update_log_display(self, recent_logs):
        """Update the log display widget with the most recent logs"""
        self.log_display.clear()
        for log in recent_logs:
            self.log_display.append(log)
        
        # Scroll to the bottom to show latest logs
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if folder_path:
            self.config["targetPath"] = folder_path
            self.path_display.setText(folder_path)
            
            # Save to JSON
            with open(self.config_file, "w") as f:
                json.dump(self.config, f)
            
            self.safe_log_message(f"Download folder set to: {folder_path}")

    # Thread-safe logging methods
    def safe_log_message(self, message):
        """Thread-safe method to log a message"""
        print(message)  # This will go through the logger
    
    @Slot(str)
    def handle_log_message(self, message):
        """Handle log messages from worker thread"""
        print(message)  # This will go through the logger
        self.log_display_data.add_line(message)
        self.update_log_display(self.log_display_data.get_lines())
    
    @Slot(str)
    def handle_download_started(self, url):
        """Handle download start from worker thread"""
        print(f"Downloading: {url}")
        self.log_display_data.add_line(f"Downloading: {url}")
        self.update_log_display(self.log_display_data.get_lines())
    @Slot(str)
    def handle_download_complete(self, url):
        """Handle download completion from worker thread"""
        print(f"Download completed successfully: {url}")
        self.log_display_data.add_line(f"Download completed successfully: {url}")
        self.update_log_display(self.log_display_data.get_lines())
    
    @Slot(str, str)
    def handle_download_error(self, url, error):
        """Handle download errors from worker thread"""
        print(f"Download failed for {url}: {error}")

    def run_handle_download_queue(self):
        """Worker thread function to process download queue"""
        #downloader = Downloader()
        while self._running:
            if self.queue_download.empty():
                #print("Queue is empty, sleeping for 1 second...")
                sleep(1)
                continue
            
            try:
                input_string = self.queue_download.get()
                # Use signal to log from the worker thread
                self.worker_signals.log_message.emit(f"Processing download: {input_string}")
                
                # Get target path from config
                target_path = self.config.get("targetPath", "")
                if not target_path:
                    self.worker_signals.log_message.emit("Error: No download folder selected")
                    self.worker_signals.download_error.emit(input_string, "No download folder selected")
                    self.queue_download.task_done()
                    continue
                    
                self.worker_signals.log_message.emit(f"Starting download of: {input_string}")
                self.worker_signals.log_message.emit(f"Save path: {target_path}")
                
                # Call the downloader with the URL and target path
                self._downloader.download(input_string, target_path)
                
                # Signal completion
                self.worker_signals.download_complete.emit(input_string)
                self.queue_download.task_done()
                
            except Exception as e:
                error_msg = str(e)
                self.worker_signals.log_message.emit(f"Error in download thread: {error_msg}")
                if input_string:
                    self.worker_signals.download_error.emit(input_string, error_msg)
                self.queue_download.task_done()
            
            # Short sleep to prevent CPU hogging
            sleep(0.1)

    def run_function(self):
        """Add URL to download queue when button is clicked or Enter is pressed"""
        input_text = self.line_edit.text().strip()
        if input_text:
            self.queue_download.put(input_text)
            self.safe_log_message(f"Added to download queue: {input_text}")
            
            # Clear the input field
            self.line_edit.clear()
            
            # Show confirmation
            current_queue_size = self.queue_download.qsize()
            if current_queue_size > 1:
                self.queue_status.setText(f"Downloads in queue: {current_queue_size}")
            else:
                self.queue_status.setText("Processing download...")
    
    def closeEvent(self, event):
        # Hide the window instead of closing the application
        event.ignore()
        self.hide()
        self.safe_log_message("Application minimized to system tray")
    
    def shutdown(self):
        """Clean shutdown of the application"""
        self.safe_log_message("Shutting down application...")
        self._running = False
        
        # Wait for the download thread to finish (with timeout)
        if self.thread_handle_download_queue.is_alive():
            self.thread_handle_download_queue.join(timeout=2.0)


class SystemTrayApp(QApplication):
    def __init__(self, argv, logger):
        super().__init__(argv)
        
        self.logger = logger
        self.main_window = MainWindow(logger)
        self.main_window.show()
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Using a standard icon from QStyle
        self.tray_icon.setIcon(QIcon(self.style().standardPixmap(QStyle.SP_DriveFDIcon)))
        self.tray_icon.setToolTip("Video Downloader")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.main_window.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Handle tray icon activation
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Show or hide the main window when the tray icon is clicked
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.main_window.show()
                self.main_window.raise_()  # Bring to front
    
    def quit_app(self):
        """Properly shutdown the application"""
        self.main_window.shutdown()
        self.logger.close()
        super().quit()


if __name__ == "__main__":
    # Initialize the logger
    logger = TerminalLogger()
    
    # Start the application
    app = SystemTrayApp(sys.argv, logger)
    sys.exit(app.exec())