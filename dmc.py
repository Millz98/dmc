from pytube import YouTube, Playlist
from tqdm import tqdm
import requests
import os
from moviepy.editor import AudioFileClip
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QRadioButton

class DMCApp(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        # Widgets
        self.label_url = QLabel("Enter the URL of the YouTube video or playlist you want to download:")
        self.url_input = QLineEdit(self)
        self.destination_input = QLineEdit(self)
        self.destination_input.setPlaceholderText("Enter the destination folder path")
        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_destination)

        self.radio_audio = QRadioButton("MP3 (Audio)")
        self.radio_video = QRadioButton("MP4 (Video)")
        
        self.download_button = QPushButton("Download", self)
        self.download_button.clicked.connect(self.download)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label_url)
        layout.addWidget(self.url_input)
        layout.addWidget(self.destination_input)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.radio_audio)
        layout.addWidget(self.radio_video)
        layout.addWidget(self.download_button)

        self.setLayout(layout)

    def browse_destination(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        self.destination_input.setText(folder_path)

    def download(self):
        url = self.url_input.text()
        destination = self.destination_input.text()

        if not url or not destination:
            print("Please enter both URL and destination folder.")
            return

        try:
            yt = YouTube(url)

            # Print video information
            print_video_information(yt)

            # Download the chosen file
            choice = 1 if self.radio_audio.isChecked() else 2

            if "/playlist" in url:
                download_playlist(url, choice, destination)
            else:
                download_video(yt, choice, destination)

            # Result of success
            print(f"{yt.title} has been successfully downloaded.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def print_video_information(yt):
    print(f"Title: {yt.title}")
    print(f"Duration: {yt.length} seconds")
    print(f"Upload Date: {yt.publish_date}")
    print(f"View Count: {yt.views}")
    print(f"Description: {yt.description}")
    print()

def download_audio(yt, destination):
    # get the best quality stream for audio
    audio_stream = yt.streams.filter(only_audio=True).order_by('abr').last()

    # create a progress bar for audio download
    with tqdm(total=audio_stream.filesize, unit='B', unit_scale=True, unit_divisor=1024, desc='Audio') as bar:
        with requests.get(audio_stream.url, stream=True) as response:
            with open(os.path.join(destination, audio_stream.default_filename), 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        bar.update(1024)

    # save the audio file as MP3 using moviepy
    base, _ = os.path.splitext(os.path.join(destination, audio_stream.default_filename))
    audio_new_file = base + '.mp3'
    
    # Convert audio file to MP3 using MoviePy
    audio_clip = AudioFileClip(os.path.join(destination, audio_stream.default_filename))
    audio_clip.write_audiofile(audio_new_file, codec='mp3')
    audio_clip.close()

    # remove the original audio file
    os.remove(os.path.join(destination, audio_stream.default_filename))

def download_video_file(yt, destination):
    # get the best quality stream for video
    video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').last()

    # create a progress bar for video download
    with tqdm(total=video_stream.filesize, unit='B', unit_scale=True, unit_divisor=1024, desc='Video') as bar:
        with requests.get(video_stream.url, stream=True) as response:
            with open(os.path.join(destination, video_stream.default_filename), 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        bar.update(1024)

def download_video(yt, choice, destination):
    try:
        # Print video information
        print_video_information(yt)

        # Download the chosen file
        if choice == 1:
            download_audio(yt, destination)
        else:
            download_video_file(yt, destination)

        # Result of success
        print(yt.title + " has been successfully downloaded.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def download_playlist(playlist_url, choice, destination):
    try:
        playlist = Playlist(playlist_url)

        for video_url in playlist.video_urls:
            try:
                yt = YouTube(video_url)
                download_audio(yt, destination)
            except Exception as e:
                print(f"Error processing video {video_url}: {str(e)}")

        print("Playlist has been successfully downloaded.")
    except Exception as e:
        print(f"An error occurred while processing the playlist: {str(e)}")

def main():
    app = QApplication([])
    window = DMCApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()