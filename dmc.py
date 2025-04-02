import os
import sys
import subprocess
import json
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QRadioButton, QProgressBar, QMessageBox, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject

# Check if yt-dlp is installed, if not, install it
try:
    import yt_dlp
    print("yt-dlp is already installed")
except ImportError:
    print("Installing yt-dlp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

# Check if FFmpeg is installed
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

class VideoProcessor(QObject):
    print_information_signal = pyqtSignal(str)

    def print_video_information(self, info_dict):
        try:
            if 'entries' in info_dict:  # It's a playlist
                info_str = f"Playlist: {info_dict.get('title', 'Unknown')}\n"
                info_str += f"Number of videos: {len(info_dict['entries'])}\n"
                # Show info for the first video
                if info_dict['entries']:
                    first_video = info_dict['entries'][0]
                    info_str += f"\nFirst video: {first_video.get('title', 'Unknown')}\n"
                    info_str += f"Duration: {first_video.get('duration', 'Unknown')} seconds\n"
                    info_str += f"Channel: {first_video.get('uploader', 'Unknown')}\n"
            else:  # It's a single video
                info_str = (
                    f"Video Title: {info_dict.get('title', 'Unknown')}\n"
                    f"Video Duration: {info_dict.get('duration', 'Unknown')} seconds\n"
                    f"Channel: {info_dict.get('uploader', 'Unknown')}\n"
                    f"Upload Date: {info_dict.get('upload_date', 'Unknown')}\n"
                    f"Video URL: {info_dict.get('webpage_url', 'Unknown')}\n"
                )
                
                view_count = info_dict.get('view_count')
                if view_count:
                    info_str += f"Number of Views: {view_count}\n"
                    
                like_count = info_dict.get('like_count')
                if like_count:
                    info_str += f"Number of Likes: {like_count}\n"
                
                # Get resolution if available
                height = info_dict.get('height')
                width = info_dict.get('width')
                if height and width:
                    info_str += f"Resolution: {width}x{height}\n"
                
                # Get filesize if available
                filesize = info_dict.get('filesize')
                if filesize:
                    info_str += f"File Size: {filesize / (1024 * 1024):.2f} MB\n"
                
            self.print_information_signal.emit(info_str)
        except Exception as e:
            self.print_information_signal.emit(f"Error getting video information: {str(e)}")

class DownloadThread(QThread):
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    info_update = pyqtSignal(dict)

    def __init__(self, url, choice, destination):
        super().__init__()
        self.url = url
        self.choice = choice  # 1 for audio, 2 for video
        self.destination = destination
        
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                self.progress_update.emit(int(percent))
                self.status_update.emit(f"Downloading: {percent:.1f}%")
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                self.progress_update.emit(int(percent))
                self.status_update.emit(f"Downloading: {percent:.1f}%")
        elif d['status'] == 'finished':
            self.progress_update.emit(100)
            self.status_update.emit("Download finished. Processing file...")
        elif d['status'] == 'error':
            self.download_error.emit(f"Download error: {d.get('error', 'Unknown error')}")

    def run(self):
        try:
            # Check if FFmpeg is installed
            if not check_ffmpeg():
                self.download_error.emit("FFmpeg is not installed. Please install FFmpeg to merge audio and video.")
                return
                
            self.status_update.emit(f"Initializing download for: {self.url}")
            
            # Make sure destination exists
            os.makedirs(self.destination, exist_ok=True)
            
            # Base options for both audio and video
            ydl_opts = {
                'quiet': False,  # Show output for debugging
                'verbose': True,  # More detailed output
                'progress_hooks': [self.progress_hook],
                'outtmpl': os.path.join(self.destination, '%(title)s.%(ext)s'),
                'ignoreerrors': True,  # Skip videos that cannot be downloaded
            }
            
            if self.choice == 1:  # Audio (MP3)
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                })
                self.status_update.emit("Downloading audio in MP3 format...")
            else:  # Video (MP4) - USING A SIMPLER APPROACH
                # Force format 18 which is a progressive format (audio+video together)
                # or format 22 which is HD with audio
                ydl_opts.update({
                    # Use format that already has audio and video together
                    'format': '22/18/best',  # Try HD, then standard, then any best available
                    'merge_output_format': 'mp4',
                })
                
                self.status_update.emit("Downloading video in MP4 format...")
            
            # First get info to display
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.url, download=False)
                self.info_update.emit(info_dict)
                
                # Now download
                ydl.download([self.url])
            
            self.status_update.emit("Download completed!")
            self.download_complete.emit()
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.download_error.emit(error_message)

class DMCApp(QWidget):
    def __init__(self):
        super().__init__()

        self.download_thread = None
        self.video_processor = VideoProcessor()
        self.video_processor.print_information_signal.connect(self.display_video_info)
        self.download_queue = []
        self.processing_queue = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_queue)
        
        self.init_ui()
        
        # Check for FFmpeg at startup
        if not check_ffmpeg():
            self.show_warning_message("FFmpeg not detected", 
                "FFmpeg is required for proper audio/video merging. Without it, you may get separate audio and video files.\n\n"
                "Please install FFmpeg to ensure the best results.")

    def init_ui(self):
        self.setWindowTitle("DMC - YouTube Downloader (yt-dlp version)")
        self.resize(600, 500)  # Make the window larger for more information

        main_layout = QVBoxLayout()
        
        # URL input section
        url_layout = QVBoxLayout()
        self.label_url = QLabel("Enter the URL of the YouTube video or playlist:")
        self.edit_url = QLineEdit(self)
        self.edit_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        url_layout.addWidget(self.label_url)
        url_layout.addWidget(self.edit_url)
        main_layout.addLayout(url_layout)
        
        # Destination section
        dest_layout = QHBoxLayout()
        self.label_destination = QLabel("Destination:")
        self.edit_destination = QLineEdit(self)
        self.edit_destination.setPlaceholderText("Choose download location...")
        self.button_browse = QPushButton("Browse", self)
        self.button_browse.clicked.connect(self.browse_destination)
        dest_layout.addWidget(self.label_destination)
        dest_layout.addWidget(self.edit_destination)
        dest_layout.addWidget(self.button_browse)
        main_layout.addLayout(dest_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        self.label_format = QLabel("Choose download format:")
        self.radio_audio = QRadioButton("MP3 (Audio)")
        self.radio_video = QRadioButton("MP4 (Video)")
        self.radio_audio.setChecked(True)  # Default to audio
        format_layout.addWidget(self.label_format)
        format_layout.addWidget(self.radio_audio)
        format_layout.addWidget(self.radio_video)
        main_layout.addLayout(format_layout)
        
        # Download button
        self.button_download = QPushButton("Download", self)
        self.button_download.clicked.connect(self.enqueue_download)
        main_layout.addWidget(self.button_download)
        
        # Progress section
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        main_layout.addLayout(progress_layout)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel("Video Information:"))
        self.info_label = QLabel(self)
        self.info_label.setAlignment(Qt.AlignLeft)
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(self.info_label)
        main_layout.addLayout(info_layout)
        
        self.setLayout(main_layout)

    def browse_destination(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder_path:
            self.edit_destination.setText(folder_path)

    def display_video_info(self, info):
        self.info_label.setText(info)

    def enqueue_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.show_error_message("Download is already in progress. Please wait.")
            return

        url = self.edit_url.text()
        destination = self.edit_destination.text()

        if not url:
            self.show_error_message("Please enter a YouTube URL.")
            return
            
        if not destination:
            destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
            if not destination:
                self.show_error_message("Please select a destination folder.")
                return
            self.edit_destination.setText(destination)

        choice = 1 if self.radio_audio.isChecked() else 2

        try:
            # yt-dlp natively handles playlists, so we just add the URL to the queue
            self.download_queue.append((url, choice, destination))
            self.status_label.setText("Added to queue. Starting download...")
            self.process_queue()
                
        except Exception as e:
            self.show_error_message(f"An error occurred: {str(e)}")

    def process_queue(self):
        if not self.processing_queue and self.download_queue:
            self.processing_queue = True
            url, choice, destination = self.download_queue.pop(0)
            
            # Show what's being downloaded
            self.status_label.setText(f"Initializing download...")
            
            self.download_thread = DownloadThread(url, choice, destination)
            self.download_thread.progress_update.connect(self.update_progress)
            self.download_thread.status_update.connect(self.update_status)
            self.download_thread.download_complete.connect(self.download_finished)
            self.download_thread.download_error.connect(self.show_error_message)
            self.download_thread.info_update.connect(self.process_video_info)
            self.download_thread.finished.connect(self.set_queue_flag_false)

            self.download_thread.start()

    def process_video_info(self, info_dict):
        self.video_processor.print_video_information(info_dict)

    def update_status(self, message):
        self.status_label.setText(message)

    def download_finished(self):
        self.progress_bar.setValue(100)
        
        # Check if there are more items in the queue
        if self.download_queue:
            remaining = len(self.download_queue)
            self.status_label.setText(f"Download complete. {remaining} items remaining in queue.")
        else:
            self.status_label.setText("All downloads completed!")
            self.reset_ui()

    def reset_ui(self):
        self.edit_url.clear()
        self.progress_bar.setValue(0)

    def show_error_message(self, message):
        self.status_label.setText("Error occurred")
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText("Error")
        error_dialog.setInformativeText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

    def show_warning_message(self, title, message):
        warning_dialog = QMessageBox(self)
        warning_dialog.setIcon(QMessageBox.Warning)
        warning_dialog.setText(title)
        warning_dialog.setInformativeText(message)
        warning_dialog.setWindowTitle("Warning")
        warning_dialog.exec_()

    def show_info_message(self, message):
        info_dialog = QMessageBox(self)
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.setText("Information")
        info_dialog.setInformativeText(message)
        info_dialog.setWindowTitle("Info")
        info_dialog.exec_()

    def set_queue_flag_false(self):
        self.processing_queue = False
        self.process_queue()  # Try to process the next item in queue

    def update_progress(self, value):
        self.progress_bar.setValue(value)

def main():
    app = QApplication([])
    window = DMCApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()