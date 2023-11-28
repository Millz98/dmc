from pytube import YouTube, Playlist
from tqdm import tqdm
import requests
import os
from moviepy.editor import AudioFileClip

os.environ["IMAGEIO_FFMPEG_EXE"] = "/opt/homebrew/opt/ffmpeg"

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

# Example usage
choice = int(input("Choose download format:\n1. MP3 (Audio)\n2. MP4 (Video)\nEnter your choice (1 or 2): "))

download_option = int(input("Choose download option:\n1. Single Video\n2. Entire Playlist\nEnter your choice (1 or 2): "))

if download_option == 1:
    # Download a single video
    video_url = input("Enter the URL of the YouTube video you want to download: ")
    destination = input("Enter the full path to the destination folder (e.g., D:\\Downloads): ")

    try:
        yt = YouTube(video_url)
        download_video(yt, choice, destination)
    except Exception as e:
        print(f"Error processing video {video_url}: {str(e)}")

elif download_option == 2 and choice == 2:
    # Download an entire playlist for video
    playlist_url = input("Enter the URL of the YouTube playlist you want to download: ")
    destination = input("Enter the full path to the destination folder (e.g., D:\\Downloads): ")

    download_playlist(playlist_url, choice, destination)

elif download_option == 2 and choice == 1:
    print("Downloading audio does not support playlist downloads.")

else:
    print("Invalid download option.")
