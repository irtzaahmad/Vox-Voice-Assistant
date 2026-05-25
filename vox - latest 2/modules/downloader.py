"""
Vox Download Manager Module
Handles YouTube video/audio downloads and general file downloads
Uses yt-dlp for YouTube and requests for direct downloads
"""
import os
import re
import requests
from urllib.parse import urlparse
from typing import Tuple, Optional
import config

class DownloadManager:
    def __init__(self):
        self.download_dir = config.DOWNLOADS_DIR
        self.max_size = config.MAX_DOWNLOAD_SIZE
        self.youtube_quality = config.YOUTUBE_QUALITY

        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)

    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube link"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)',
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?',
            r'(?:https?://)?(?:www\.)?youtu\.be/'
        ]

        for pattern in youtube_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def download_youtube(self, url: str, audio_only: bool = False) -> Tuple[bool, str]:
        """Download YouTube video or audio using yt-dlp"""
        try:
            import yt_dlp

            # Set download options
            if audio_only:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                    'noplaylist': True,
                }
                print(f"🎵 Downloading audio from YouTube...")
            else:
                ydl_opts = {
                    'format': self.youtube_quality,
                    'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                    'noplaylist': True,
                }
                print(f"🎬 Downloading video from YouTube...")

            # Download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                filename = ydl.prepare_filename(info)

                # Adjust filename for audio
                if audio_only:
                    filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')

                return True, f"Downloaded: {title}\nSaved to: {filename}"

        except ImportError:
            return False, "yt-dlp not installed. Run: pip install yt-dlp"
        except Exception as e:
            error_msg = str(e)
            if "ffmpeg" in error_msg.lower():
                return False, "FFmpeg not found! Please install FFmpeg to download audio. See INSTALLATION.md for instructions."
            return False, f"Error downloading: {error_msg}"

    def download_file(self, url: str, filename: str = None) -> Tuple[bool, str]:
        """Download file from direct URL"""
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL"

            # Get filename from URL if not provided
            if not filename:
                filename = os.path.basename(parsed.path)
                if not filename:
                    filename = "downloaded_file"

            filepath = os.path.join(self.download_dir, filename)

            print(f"⬇️ Downloading: {filename}")

            # Download with progress
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Check file size
            total_size = int(response.headers.get('content-length', 0))
            if total_size > self.max_size:
                return False, f"File too large ({total_size / 1024 / 1024:.1f} MB)"

            # Download
            downloaded = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Show progress for large files
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) < 8192:  # Update every MB
                                print(f"   Progress: {percent:.1f}%")

            # Get actual file size
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)

            return True, f"Downloaded: {filename} ({size_mb:.2f} MB)\nSaved to: {filepath}"

        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Error downloading: {str(e)}"

    def download(self, url: str, audio_only: bool = False, filename: str = None) -> Tuple[bool, str]:
        """Universal download method"""
        if self.is_youtube_url(url):
            return self.download_youtube(url, audio_only)
        else:
            return self.download_file(url, filename)

    def get_downloads_list(self) -> list:
        """Get list of downloaded files"""
        try:
            files = []
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'date': stat.st_mtime
                    })
            return sorted(files, key=lambda x: x['date'], reverse=True)
        except Exception as e:
            return []

    def clear_downloads(self) -> Tuple[bool, str]:
        """Clear all downloads"""
        try:
            for filename in os.listdir(self.download_dir):
                filepath = os.path.join(self.download_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            return True, "All downloads cleared"
        except Exception as e:
            return False, f"Error clearing downloads: {str(e)}"

# Test
if __name__ == "__main__":
    dm = DownloadManager()

    print("Testing Download Manager...")
    print(f"Download directory: {dm.download_dir}")

    # Test YouTube detection
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.google.com"
    ]

    for url in test_urls:
        is_yt = dm.is_youtube_url(url)
        print(f"\n{url}\nIs YouTube: {is_yt}")


