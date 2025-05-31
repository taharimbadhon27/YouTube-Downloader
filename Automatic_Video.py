import subprocess
import time
import os
import sys
import threading
from pathlib import Path

class TextStyles:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @classmethod
    def header(cls, text):
        return f"\n{cls.BOLD}{cls.BLUE}🌟 {text} 🌟{cls.END}\n"

    @classmethod
    def section(cls, text):
        return f"\n{cls.BOLD}{cls.CYAN}▬▬▶ {text} ◀▬▬{cls.END}"

    @classmethod
    def success(cls, text):
        return f"{cls.GREEN}✅ {text}{cls.END}"

    @classmethod
    def warning(cls, text):
        return f"{cls.YELLOW}⚠️ {text}{cls.END}"

    @classmethod
    def fail(cls, text):
        return f"{cls.RED}❌ {text}{cls.END}"

    @classmethod
    def progress(cls, text):
        return f"{cls.BLUE}⏳ {text}{cls.END}"

    @classmethod
    def download(cls, text):
        return f"{cls.GREEN}📥 {text}{cls.END}"

    @classmethod
    def pretty_path(cls, path):
        return f"{cls.CYAN}📁 {path}{cls.END}"

class Spinner:
    def __init__(self, message):
        self.spinner_chars = '⣾⣽⣻⢿⡿⣟⣯⣷'
        self.message = message
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.spin)

    def spin(self):
        i = 0
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r{self.spinner_chars[i]} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(self.spinner_chars)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
        sys.stdout.flush()

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

# CONFIGURATION
DOWNLOAD_DIR = str(Path.home() / "storage/shared/Movies")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def check_environment():
    """Verify all requirements are installed"""
    spinner = Spinner("Checking environment...")
    spinner.start()
    
    try:
        # Basic environment check
        if not os.path.exists("/data/data/com.termux/files/home"):
            spinner.stop()
            print(TextStyles.fail("Please run this in Termux environment"))
            return False

        # Show yt-dlp version
        version = subprocess.run(["yt-dlp", "--version"], 
                               check=True, 
                               capture_output=True, 
                               text=True)
        spinner.stop()
        print(TextStyles.success(f"Using yt-dlp version {version.stdout.strip()}"))

        # Verify download directory
        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
        print(TextStyles.pretty_path(f"Download directory: {DOWNLOAD_DIR}"))

        return True

    except subprocess.CalledProcessError:
        spinner.stop()
        print(TextStyles.fail("Please install yt-dlp: pip install yt-dlp"))
        return False
    except Exception as e:
        spinner.stop()
        print(TextStyles.fail(f"Setup issue: {str(e)}"))
        return False

def get_clipboard_content():
    """Get clipboard content"""
    try:
        result = subprocess.run(["termux-clipboard-get"],
                              capture_output=True,
                              text=True,
                              check=True)
        return result.stdout.strip()
    except Exception:
        return ""

def is_video_url(url):
    """Check if URL is from supported platforms"""
    domains = [
        "facebook.com", "fb.watch",
        "instagram.com", "tiktok.com",
        "youtube.com", "youtu.be",
        "twitter.com", "x.com",
        "vimeo.com", "dailymotion.com"
    ]
    return any(domain in url.lower() for domain in domains) if url else False

def simple_download(url):
    """Simplified download as fallback"""
    try:
        subprocess.run([
            "yt-dlp",
            "-f", "best",
            "--user-agent", USER_AGENT,
            "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            url
        ], check=True)
        return True
    except Exception:
        return False

def download_video(url):
    """Download video with platform-specific handling"""
    if not url or not is_video_url(url):
        return False

    print(TextStyles.section("Starting Download"))
    print(TextStyles.progress(f"Processing: {url}"))

    try:
        # Platform-specific handling
        if "facebook.com" in url.lower() or "fb.watch" in url.lower():
            cmd = [
                "yt-dlp",
                "-f", "best",
                "--user-agent", USER_AGENT,
                "--referer", "https://www.facebook.com/",
                "--no-check-certificate",
                "--merge-output-format", "mp4",
                "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                url
            ]
        elif "instagram.com" in url.lower():
            cmd = [
                "yt-dlp",
                "-f", "best",
                "--user-agent", USER_AGENT,
                "--cookies-from-browser", "firefox",
                "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                url
            ]
        elif "tiktok.com" in url.lower():
            cmd = [
                "yt-dlp",
                "-f", "best",
                "--user-agent", USER_AGENT,
                "--referer", "https://www.tiktok.com/",
                "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                url
            ]
        else:  # Default (YouTube etc)
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "--user-agent", USER_AGENT,
                "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                url
            ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            if '[download]' in line:
                print(TextStyles.download(line.strip()))
            elif 'ERROR' in line:
                print(TextStyles.fail(line.strip()))
            else:
                print(line.strip())

        process.wait()
        
        if process.returncode == 0:
            print(TextStyles.success("\n🎉 Download completed successfully!"))
            return True
        else:
            print(TextStyles.warning("\n⚠️ Trying alternative method..."))
            # Fallback to generic download
            return simple_download(url)

    except Exception as e:
        print(TextStyles.fail(f"\n❌ Download error: {str(e)}"))
        return False

def main():
    print(TextStyles.header("Social Media Video Downloader"))
    print(TextStyles.progress("Monitoring clipboard for video links..."))
    
    if not check_environment():
        print(TextStyles.fail("Exiting due to setup issues"))
        sys.exit(1)

    last_downloaded = ""
    try:
        while True:
            clipboard_content = get_clipboard_content()
            
            if clipboard_content and clipboard_content != last_downloaded and is_video_url(clipboard_content):
                print(TextStyles.section("New Video Found"))
                print(TextStyles.progress(f"URL: {clipboard_content}"))
                if download_video(clipboard_content):
                    last_downloaded = clipboard_content
                    print(TextStyles.success("Ready for next download"))
                else:
                    print(TextStyles.warning("Will try again with next link"))
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print(TextStyles.header("Thank you for using Social Media Video Downloader!"))
    except Exception as e:
        print(TextStyles.fail(f"Unexpected error: {str(e)}"))

if __name__ == "__main__":
    main()