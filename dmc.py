from pytube import YouTube, Playlist
import requests
import os
from moviepy.editor import AudioFileClip
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QRadioButton, QProgressBar, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject, QMetaObject
from qtawesome import icon

# VideoProcessor class processes video information and emits signals for UI update
class VideoProcessor(QObject):
    print_information_signal = pyqtSignal(str)

    def print_video_information(self, yt):
        # Construct a string with video information
        info_str = (
            f"Video Title: {yt.title}\n"
            f"Video Duration: {yt.length} seconds\n"
            f"Video Resolution: {yt.streams.get_highest_resolution().resolution}\n"
            f"Video Format: {yt.streams.get_highest_resolution().mime_type}\n"
            f"Audio Codec: {yt.streams.get_audio_only().abr} kbps\n"
            f"Video Codec: {yt.streams.get_highest_resolution().video_codec}\n"
            f"File Size: {yt.streams.get_highest_resolution().filesize / (1024 * 1024):.2f} MB\n"
            f"Number of Views: {yt.views}\n"
            f"Video URL: {yt.watch_url}"
        )
        # Emit a signal with the information string
        self.print_information_signal.emit(info_str)

# Downloader class handles the download process in a separate thread
class DownloadThread(QThread):
    progress_update = pyqtSignal(int)
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)
    update_progress_signal = pyqtSignal(int)  # Add this line

    def __init__(self, yt, choice, destination, video_processor):
        super().__init__()
        self.yt = yt
        self.choice = choice
        self.destination = destination
        self.video_processor = video_processor
        


    def run(self):
        try:
            # Check the user's choice and call appropriate download method
            if self.choice == 1:
                self.download_audio()
            else:
                self.download_video_file()

                self.update_progress_signal.connect(self.progress_update)

      

            # Notify UI that the download is complete
            print(f"{self.yt.title} has been successfully downloaded.")
            self.download_complete.emit()
        except Exception as e:
            # Emit an error signal if an exception occurs during download
            error_message = f"An error occurred: {str(e)}"
            self.download_error.emit(error_message)

    # Download audio stream and convert it to MP3
    def download_audio(self):
        audio_stream = self.yt.streams.filter(only_audio=True).order_by('abr').last()

        with requests.get(audio_stream.url, stream=True) as response:
            with open(os.path.join(self.destination, audio_stream.default_filename), 'wb') as f:
                self._download_with_progress(response, f)

        base, _ = os.path.splitext(os.path.join(self.destination, audio_stream.default_filename))
        audio_new_file = base + '.mp3'
        self._convert_audio_format(audio_stream.default_filename, audio_new_file)

    # Download video stream
    def download_video_file(self):
        yt = YouTube(self.yt.watch_url)
        video_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
        video_stream = video_streams.first()

        with requests.get(video_stream.url, stream=True) as response:
            with open(os.path.join(self.destination, video_stream.default_filename), 'wb') as f:
                self._download_with_progress(response, f)

        # Print video information and update progress to 100%
        self.video_processor.print_video_information(yt)
        self.progress_update.emit(100)

    # Helper method to download content with progress updates
    def _download_with_progress(self, response, file):
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        for data in response.iter_content(chunk_size=1024):
            downloaded += len(data)
            file.write(data)
            progress = int((downloaded / total_size) * 100)
            self.progress_update.emit(progress)

    # Helper method to convert audio format to MP3
    def _convert_audio_format(self, input_file, output_file):
        audio_clip = AudioFileClip(os.path.join(self.destination, input_file))
        audio_clip.write_audiofile(output_file, codec='mp3')
        audio_clip.close()

        os.remove(os.path.join(self.destination, input_file))

# DMCApp class represents the main application window
class DMCApp(QWidget):
    def __init__(self):
        super().__init__()

        self.download_thread = None
        self.init_ui()
        self.video_processor = VideoProcessor()
        self.download_queue = []
        self.processing_queue = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_queue)
        update_progress_signal = pyqtSignal(int)

        if self.download_thread:
            self.download_thread.download_error.connect(self.show_error_message)

    def init_ui(self):
        self.label_url = QLabel("Enter the URL of the YouTube video or playlist:")
        self.edit_url = QLineEdit(self)
        self.button_browse = QPushButton("Browse", self)
        self.button_browse.clicked.connect(self.browse_destination)
        self.setWindowTitle("DMC")  # Set the window title to "DMC"

        self.label_format = QLabel("Choose download format:")
        self.radio_audio = QRadioButton("MP3 (Audio)")
        self.radio_video = QRadioButton("MP4 (Video)")

        if self.download_thread:
            self.download_thread.download_complete.connect(self.reset_ui)

        self.button_download = QPushButton("Download", self)
        self.button_download.clicked.connect(self.enqueue_download)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)

        self.progress_label = QLabel(self)
        self.progress_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.label_url)
        layout.addWidget(self.edit_url)
        layout.addWidget(self.button_browse)
        layout.addWidget(self.label_format)
        layout.addWidget(self.radio_audio)
        layout.addWidget(self.radio_video)
        layout.addWidget(self.button_download)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        self.setLayout(layout)

    # Browse for the destination folder
    def browse_destination(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        self.edit_url.setText(folder_path)

    # Enqueue a download request
    def enqueue_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.show_error_message("Download is already in progress. Please wait.")
            return

        url = self.edit_url.text()
        destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder")

        if not url or not destination:
            self.show_error_message("Please enter both URL and destination folder.")
            return

        try:
            yt = YouTube(url)
            choice = 1 if self.radio_audio.isChecked() else 2

            if "/playlist" in url:
                self.enqueue_playlist(url, choice, destination)
            else:
                self.download_queue.append((yt, choice, destination))
                self.process_queue()

        except Exception as e:
            self.show_error_message(f"An error occurred: {str(e)}")

    # Enqueue a playlist for download
    def enqueue_playlist(self, playlist_url, choice, destination):
        try:
            playlist = Playlist(playlist_url)

            for video_url in playlist.video_urls:
                try:
                    yt = YouTube(video_url)
                    self.download_queue.append((yt, choice, destination))
                except Exception as e:
                    self.show_error_message(f"Error processing video {video_url}: {str(e)}")

            print("Playlist has been enqueued.")
            self.process_queue()

        except Exception as e:
            self.show_error_message(f"An error occurred while processing the playlist: {str(e)}")

    # Process the download queue
    def process_queue(self):
        if not self.processing_queue and self.download_queue:
            self.processing_queue = True
            yt, choice, destination = self.download_queue.pop(0)
            self.download_thread = DownloadThread(yt, choice, destination, self.video_processor)
            self.download_thread.progress_update.connect(self.update_progress)
            self.download_thread.download_complete.connect(self.reset_ui)
            self.download_thread.download_error.connect(self.show_error_message)
            self.download_thread.finished.connect(self.set_queue_flag_false)

            self.download_thread.start()

    # Reset UI elements after a download is complete
    def reset_ui(self):
        self.edit_url.clear()
        self.radio_audio.setChecked(False)
        self.radio_video.setChecked(False)
        self.progress_bar.setValue(0)
        self.progress_label.clear()
        self.process_queue()

    # Show an error message dialog
    def show_error_message(self, message):
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText("Error")
        error_dialog.setInformativeText(message)
        error_dialog.setWindowTitle("Error")
        error_dialog.exec_()

    # Set the processing flag to false after a download is complete
    def set_queue_flag_false(self):
        self.processing_queue = False

    # Update the progress bar and label during a download
    def update_progress(self, value):
        # Update the progress bar directly without using invokeMethod
        self.progress_bar.setValue(value)
        percentage = f"{value}%"
        self.progress_label.setText(percentage)

        if value == 100:
            self.progress_label.setText("Complete")
            self.timer.start(3000)

        

# Main function to run the application
def main():
    app = QApplication([])
    window = DMCApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
