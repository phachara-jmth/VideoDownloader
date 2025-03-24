import yt_dlp as dlp
import os

class Downloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best'
        }

    def download(self, video_page_url, path):
        if path:  # Check if path is not empty
            os.makedirs(path, exist_ok=True)
            self.ydl_opts['outtmpl'] = os.path.join(path, '%(title)s.%(ext)s')
        else:
            self.ydl_opts['outtmpl'] = '%(title)s.%(ext)s'  # Save in the current directory

        with dlp.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([video_page_url])

# Example usage:
# downloader = Downloader()
# downloader.download("https://www.youtube.com/watch?v=example", "./downloads")
