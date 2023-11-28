from pytube import YouTube
from pytube.exceptions import AgeRestrictedError
from tqdm import tqdm
import requests
import os

def download_video(yt, choice, destination):
    try:
        # get the best quality streams for audio and video
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').last()
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').last()

        # download the chosen file
        if choice == 1:
            print("Downloading audio...")

            # create a progress bar for audio download
            with tqdm(total=audio_stream.filesize, unit='B', unit_scale=True, unit_divisor=1024, desc='Audio') as bar:
                with requests.get(audio_stream.url, stream=True) as response:
                    with open(os.path.join(destination, audio_stream.default_filename), 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                bar.update(1024)

            # save the audio file as MP3
            base, _ = os.path.splitext(os.path.join(destination, audio_stream.default_filename))
            audio_new_file = base + '.mp3'
            os.rename(os.path.join(destination, audio_stream.default_filename), audio_new_file)
        else:
            print("Downloading video...")

            # create a progress bar for video download
            with tqdm(total=video_stream.filesize, unit='B', unit_scale=True, unit_divisor=1024, desc='Video') as bar:
                with requests.get(video_stream.url, stream=True) as response:
                    with open(os.path.join(destination, video_stream.default_filename), 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                bar.update(1024)

        # result of success
        print(yt.title + " has been successfully downloaded.")
    except AgeRestrictedError:
        print("This video is age-restricted and cannot be downloaded at this time.")

# url input from user
url = str(input("Enter the URL of the video you want to download: \n>> "))
yt = YouTube(url)

# ask the user for their choice
print("Choose download format:")
print("1. MP3 (Audio)")
print("2. MP4 (Video)")

choice = int(input("Enter your choice (1 or 2): "))

# check for destination to save file
print("Enter the destination (leave blank for current directory)")
destination = str(input(">> ")) or '.'

download_video(yt, choice, destination)