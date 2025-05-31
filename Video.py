# No top-level imports

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
    def input_prompt(cls, text):
        return f"{cls.BOLD}{cls.CYAN}📌 {text}{cls.END}"

    @classmethod
    def progress(cls, text):
        return f"{cls.BLUE}⏳ {text}{cls.END}"

    @classmethod
    def download(cls, text):
        return f"{cls.GREEN}📥 {text}{cls.END}"


class Spinner:
    def __init__(self, message):
        self.spinner_chars = '⣾⣽⣻⢿⡿⣟⣯⣷'
        self.message = message
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.spin)

    def spin(self):
        index = 0
        while not self.stop_event.is_set():
            sys.stdout.write(f'\r{TextStyles.BLUE}{self.spinner_chars[index]} {self.message}{TextStyles.END}')
            sys.stdout.flush()
            index = (index + 1) % len(self.spinner_chars)
            time.sleep(0.1)
        sys.stdout.write('\r\033[K')
        sys.stdout.flush()

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        self.thread.join()


def detect_platform(url):
    platform_map = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'facebook.com': 'Facebook',
        'instagram.com': 'Instagram'
    }
    for domain, platform in platform_map.items():
        if domain in url:
            return platform
    return 'Other'


def sanitize_title(title, max_length=150):
    cleaned = re.sub(r'[\\/*?:"<>|]', '', title).strip().replace('/', '-')
    return cleaned[:max_length]


def get_platform_title(info, platform):
    title = info.get('title') or info.get('fulltitle') or \
            info.get('uploader') or os.path.basename(info.get('webpage_url', 'video'))
    
    if platform in ['Facebook', 'Instagram']:
        return sanitize_title(title, max_length=20)
    return sanitize_title(title)


def get_best_format(platform):
    if platform == 'YouTube':
        return 'bestvideo[height<=1080][vcodec^=avc1]+bestaudio/best[height<=720]/best'
    return 'best'


def get_next_social_media_number(directory):
    if not os.path.exists(directory):
        return 1
        
    existing_files = [f for f in os.listdir(directory) 
                     if f.startswith('Social Media download')]
    max_number = 0
    
    for filename in existing_files:
        match = re.search(r'Social Media download (\d+)', filename)
        if match:
            current_num = int(match.group(1))
            max_number = max(max_number, current_num)
            
    return max_number + 1


def check_dependency_executable():
    import shutil  # Added import here to ensure shutil is defined
    yt_dlp_path = shutil.which("yt-dlp")
    if yt_dlp_path is None:
        print(TextStyles.fail("Error: yt-dlp executable not found. Please install yt-dlp."))
        sys.exit(1)
    return yt_dlp_path


def my_progress_hook(d):
    if d.get('status') == 'downloading':
        speed = d.get('speed') or 0
        speed_kb = speed / 1024 if speed else 0
        eta = d.get('eta') or 0
        percent = d.get('_percent_str', '').strip()
        sys.stdout.write(f"\rDownloading {d.get('filename', 'video')}: {percent} at {speed_kb:.2f} kB/s, ETA: {eta}s")
        sys.stdout.flush()
    elif d.get('status') == 'finished':
        sys.stdout.write("\nDownload complete!\n")


def download_video_subprocess(yt_dlp_path, video_url, output_directory, output_template, video_title):
    sponsorblock_categories = 'sponsor,selfpromo,interaction,intro,outro,preview'
    command = [
        yt_dlp_path,
        '--cookies', '/storage/emulated/0/YouTube/Cookies/cookies.txt',
        '--sponsorblock-remove', sponsorblock_categories,
        '--embed-thumbnail',
        '--concurrent-fragments', '5',
        '-f', 'bestvideo[height<=1080][vcodec^=avc1]+bestaudio/best[height<=720]/best',
        '-o', os.path.join(output_directory, output_template),
        video_url
    ]
    try:
        from yt_dlp import YoutubeDL
        print(TextStyles.progress("Downloading (subprocess): " + video_title))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            line = process.stdout.readline()
            if not line:
                break
            sys.stdout.write(line)
            sys.stdout.flush()
        process.wait()
        if process.returncode != 0:
            print(TextStyles.fail(f"Download failed: {video_title}"))
            return False
        print(TextStyles.success(f"Completed: {video_title}"))
        return True
    except subprocess.CalledProcessError as e:
        print(TextStyles.fail(f"Download failed: {e}"))
        return False


def main():
    # Prompt for URL and detect platform before heavy imports
    url = input(TextStyles.input_prompt("Enter URL (YouTube/Facebook/Instagram): ")).strip()
    if not url:
        print(TextStyles.fail("Invalid URL. Exiting..."))
        return

    platform = detect_platform(url)
    print(TextStyles.success(f"Detected platform: {platform}"))

    sponsor_block_active = False
    yt_dlp_executable = None
    if platform == 'YouTube':
        start_time = input(TextStyles.input_prompt("Start time (e.g., '1:00' or Enter for full video): ")).strip()
        skip_seconds = input(TextStyles.input_prompt("Seconds to skip from end (Enter for none): ")).strip() or '0'
        try:
            from yt_dlp import YoutubeDL
            skip_seconds = int(skip_seconds)
            if skip_seconds < 0:
                raise ValueError
        except ValueError:
            print(TextStyles.fail("Invalid skip seconds. Exiting..."))
            return

        if not start_time and skip_seconds == 0:
            sponsor_block_active = True
            yt_dlp_executable = check_dependency_executable()
            print(TextStyles.success("SponsorBlock is active for this download."))
    else:
        start_time = ''
        skip_seconds = 0

    # Now import heavy libraries and assign to globals
    import os
    import re
    import sys
    import time
    import threading
    import subprocess
    import shutil
    from yt_dlp import YoutubeDL

    globals()['os'] = os
    globals()['re'] = re
    globals()['sys'] = sys
    globals()['time'] = time
    globals()['threading'] = threading
    globals()['subprocess'] = subprocess
    globals()['shutil'] = shutil
    globals()['YoutubeDL'] = YoutubeDL

    base_directory = '/storage/emulated/0/YouTube/Video/'
    print(TextStyles.section("Directory Setup"))
    os.makedirs(base_directory, exist_ok=True)

    print(TextStyles.section("Content Information"))
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
        'cookiefile': '/storage/emulated/0/YouTube/Cookies/instagram_cookies.txt' if platform == 'Instagram' else '/storage/emulated/0/YouTube/Cookies/cookies.txt',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.169 Mobile Safari/537.36',
            'Referer': 'https://www.instagram.com/' if platform == 'Instagram' else 'https://www.google.com/'
        },
    }

    try:
        with Spinner("Analyzing content..."):
            with YoutubeDL(ydl_opts) as ydl:
                content_info = ydl.extract_info(url, download=False)
                entries = content_info.get('entries', [content_info])
                total_items = len(entries)
                
                if platform in ['Instagram', 'Facebook']:
                    output_directory = os.path.join(base_directory, 'Socialmedia Downloads')
                    os.makedirs(output_directory, exist_ok=True)
                    print(f"\n{TextStyles.success('Social media folder: ' + TextStyles.UNDERLINE + output_directory + TextStyles.END)}")
                elif platform == 'YouTube':
                    if total_items > 1:
                        playlist_title = sanitize_title(content_info.get('title', 'YouTube_Playlist'))
                        output_directory = os.path.join(base_directory, playlist_title)
                    else:
                        output_directory = os.path.join(base_directory, 'YouTube')
                    os.makedirs(output_directory, exist_ok=True)
                    print(f"\n{TextStyles.success('YouTube folder: ' + TextStyles.UNDERLINE + output_directory + TextStyles.END)}")
                else:
                    output_directory = os.path.join(base_directory, platform)
                    os.makedirs(output_directory, exist_ok=True)
                    print(f"\n{TextStyles.success('Output directory: ' + TextStyles.UNDERLINE + output_directory + TextStyles.END)}")
    except Exception as e:
        print(TextStyles.fail(f"Content error: {e}"))
        return

    print(TextStyles.section("Download Process"))
    print(TextStyles.progress(f"Total items found: {total_items}"))

    try:
        if platform in ['Instagram', 'Facebook']:
            item_counter = get_next_social_media_number(output_directory)
        else:
            item_counter = 1
            
        success_count = 0
        for entry in entries:
            print(f"\n{TextStyles.BOLD}{TextStyles.YELLOW}▶ Item {item_counter}/{total_items}{TextStyles.END}")
            video_url = entry.get('url') or url
            
            video_title = get_platform_title(entry, platform)
            video_duration = entry.get('duration', 0)

            if video_duration:
                end_time = max(0, float(video_duration) - skip_seconds)
                hours = int(end_time // 3600)
                minutes = int((end_time % 3600) // 60)
                seconds = int(end_time % 60)
                end_time_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                end_time_str = ''

            print(TextStyles.progress(f"Title: {video_title}"))
            if video_duration:
                print(TextStyles.progress(f"Duration: {video_duration}s | Trim: {start_time or '0:00'} - {end_time_str}"))

            if platform in ['Instagram', 'Facebook']:
                output_template = f'Social Media download {item_counter} {video_title}.%(ext)s'
            elif platform == 'YouTube' and total_items > 1:
                output_template = f'{item_counter}.{video_title}.%(ext)s'
            else:
                output_template = f'{video_title}.%(ext)s'

            if sponsor_block_active:
                success = download_video_subprocess(
                    yt_dlp_executable,
                    video_url,
                    output_directory,
                    output_template,
                    video_title
                )
                if success:
                    success_count += 1
            else:
                ydl_opts = {
                    'format': get_best_format(platform),
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(output_directory, output_template),
                    'ratelimit': 20 * 1024 * 1024,
                    'http_chunk_size': 10 * 1024 * 1024,
                    'concurrent_fragment_downloads': 10,
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }],
                    'progress_hooks': [my_progress_hook],
                    'cookiefile': '/storage/emulated/0/YouTube/Cookies/instagram_cookies.txt' if platform == 'Instagram' else '/storage/emulated/0/YouTube/Cookies/cookies.txt',
                    'headers': {
                        'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 '
                                       '(KHTML, like Gecko) Chrome/118.0.5993.169 Mobile Safari/537.36') 
                                       if platform == 'Instagram' 
                                       else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                            '(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
                    },
                    'windowsfilenames': True,
                    'postprocessor_args': []
                }

                if start_time and end_time_str:
                    ydl_opts['postprocessor_args'].extend(['-ss', start_time, '-to', end_time_str, '-vsync', '2', '-r', '30'])

                try:
                    with Spinner("Downloading..."):
                        with YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])
                    success_count += 1
                    print(TextStyles.success(f"Completed: {video_title}"))
                except Exception as e:
                    print(TextStyles.fail(f"Download failed: {e}"))

            item_counter += 1

        print(f"\n{TextStyles.BOLD}{TextStyles.GREEN}{'⎯'*40}{TextStyles.END}")
        print(TextStyles.success(f"Successfully downloaded {success_count}/{total_items} items!"))
        if platform == 'YouTube' and total_items > 1:
            print(TextStyles.success(f"Playlist location: {TextStyles.UNDERLINE}{output_directory}{TextStyles.END}"))
        else:
            print(TextStyles.success(f"Videos saved to: {TextStyles.UNDERLINE}{output_directory}{TextStyles.END}"))
        print(f"{TextStyles.GREEN}🎉 All operations completed! 🎉{TextStyles.END}")

    except Exception as e:
        print(TextStyles.fail(f"\nCritical error: {e}"))

if __name__ == "__main__":
    main()