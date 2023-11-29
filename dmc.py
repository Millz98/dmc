from pytube import YouTube, Playlist
from tqdm import tqdm
import requests
import os
from moviepy.editor import AudioFileClip
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QRadioButton, QProgressBar
from PyQt5.QtCore import Qt, QThread, pyqtSignal

def print_video_information(yt):
    print(f"Video Title: {yt.title}")
    print(f"Video Duration: {yt.length} seconds")
    print(f"Video Resolution: {yt.streams.get_highest_resolution().resolution}")
    print(f"Video Format: {yt.streams.get_highest_resolution().mime_type}")
    print(f"Audio Codec: {yt.streams.get_audio_only().abr} kbps")
    print(f"Video Codec: {yt.streams.get_highest_resolution().video_codec}")
    print(f"File Size: {yt.streams.get_highest_resolution().filesize / (1024 * 1024):.2f} MB")
    print(f"Number of Views: {yt.views}")
    print(f"Video URL: {yt.watch_url}")

class DownloadThread(QThread):
    progress_update = pyqtSignal(int)

    def __init__(self, yt, choice, destination):
        super().__init__()
        self.yt = yt
        self.choice = choice
        self.destination = destination

    def run(self):
        try:
            if self.choice == 1:
                self.download_audio()
            else:
                self.download_video_file()

            # Result of success
            print(f"{self.yt.title} has been successfully downloaded.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def download_audio(self):
        audio_stream = self.yt.streams.filter(only_audio=True).order_by('abr').last()

        with requests.get(audio_stream.url, stream=True) as response:
            with open(os.path.join(self.destination, audio_stream.default_filename), 'wb') as f:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                for data in response.iter_content(chunk_size=1024):
                    downloaded += len(data)
                    f.write(data)
                    progress = int((downloaded / total_size) * 100)
                    self.progress_update.emit(progress)

        base, _ = os.path.splitext(os.path.join(self.destination, audio_stream.default_filename))
        audio_new_file = base + '.mp3'

        audio_clip = AudioFileClip(os.path.join(self.destination, audio_stream.default_filename))
        audio_clip.write_audiofile(audio_new_file, codec='mp3')
        audio_clip.close()

        os.remove(os.path.join(self.destination, audio_stream.default_filename))

    def download_video_file(self):
        video_stream = self.yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').last()

        with requests.get(video_stream.url, stream=True) as response:
            with open(os.path.join(self.destination, video_stream.default_filename), 'wb') as f:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                for data in response.iter_content(chunk_size=1024):
                    downloaded += len(data)
                    f.write(data)
                    progress = int((downloaded / total_size) * 100)
                    self.progress_update.emit(progress)

        self.progress_update.emit(100)

class DMCApp(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.download_thread = None

    def init_ui(self):
        # Widgets
        self.label_url = QLabel("Enter the URL of the YouTube video or playlist:")
        self.edit_url = QLineEdit(self)
        self.button_browse = QPushButton("Browse", self)
        self.button_browse.clicked.connect(self.browse_destination)

        self.label_format = QLabel("Choose download format:")
        self.radio_audio = QRadioButton("MP3 (Audio)")
        self.radio_video = QRadioButton("MP4 (Video)")

        self.button_download = QPushButton("Download", self)
        self.button_download.clicked.connect(self.download)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label_url)
        layout.addWidget(self.edit_url)
        layout.addWidget(self.button_browse)
        layout.addWidget(self.label_format)
        layout.addWidget(self.radio_audio)
        layout.addWidget(self.radio_video)
        layout.addWidget(self.button_download)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def browse_destination(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        self.edit_url.setText(folder_path)

    def download(self):
        url = self.edit_url.text()
        destination = self.edit_url.text()

        if not url or not destination:
            print("Please enter both URL and destination folder.")
            return

        try:
            url = self.edit_url.text()
            destination = QFileDialog.getExistingDirectory(self, "Select Destination Folder")

            yt = YouTube(url)

            # Print video information
            print_video_information(yt)

            # Download the chosen file
            choice = 1 if self.radio_audio.isChecked() else 2

            if "/playlist" in url:
                self.download_playlist(url, choice, destination)
            else:
                self.download_thread = DownloadThread(yt, choice, destination)
                self.download_thread.progress_update.connect(self.update_progress)
                self.download_thread.start()

        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def download_playlist(self, playlist_url, choice, destination):
        try:
            playlist = Playlist(playlist_url)

            for video_url in playlist.video_urls:
                try:
                    yt = YouTube(video_url)
                    self.download_audio(yt, destination)
                except Exception as e:
                    print(f"Error processing video {video_url}: {str(e)}")

            print("Playlist has been successfully downloaded.")
        except Exception as e:
            print(f"An error occurred while processing the playlist: {str(e)}")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

def main():
    app = QApplication([])
    window = DMCApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
