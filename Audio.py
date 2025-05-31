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


def get_next_social_media_number(directory):
    existing_files = [f for f in os.listdir(directory) if f.startswith('Social Media Audio')]
    max_number = 0
    for filename in existing_files:
        match = re.search(r'Social Media Audio (\d+)', filename)
        if match:
            current_num = int(match.group(1))
            max_number = max(max_number, current_num)
    return max_number + 1


def time_to_seconds(time_str):
    parts = list(map(int, time_str.split(':')))
    seconds = 0
    for i, part in enumerate(reversed(parts)):
        seconds += part * (60 ** i)
    return seconds


class ProgressLogger:
    def __init__(self):
        self.pbar = None

    def hook(self, d):
        if d['status'] == 'downloading':
            if self.pbar is None:
                self.pbar = tqdm(
                    total=d.get('total_bytes') or d.get('downloaded_bytes'),
                    unit='B',
                    unit_scale=True,
                    desc="Downloading audio"
                )
            self.pbar.update(d['downloaded_bytes'] - self.pbar.n)
        elif d['status'] == 'finished':
            if self.pbar:
                self.pbar.close()


def embed_cover_art_with_opusenc(input_opus, thumbnail, final_opus, title, artist, date, comment):
    wav_file = input_opus.replace('.opus', '.wav')
    cmd = [
        'ffmpeg', '-hide_banner', '-loglevel', 'error',
        '-i', input_opus,
        '-c:a', 'pcm_s16le', '-ar', '48000',
        wav_file
    ]
    subprocess.run(cmd, check=True)
    cmd = [
        'opusenc', '--bitrate', '192',
        '--title', title,
        '--artist', artist,
        '--date', date,
        '--comment', comment,
        '--picture', thumbnail,
        wav_file,
        final_opus
    ]
    subprocess.run(cmd, check=True)
    os.remove(wav_file)
    print(TextStyles.success("WAV file deleted after opusenc encoding."))


def handle_youtube(url, start_seconds, end_skip_seconds):
    try:
        print(TextStyles.header("YouTube Audio Downloader"))
        output_dir = os.path.join('/storage/emulated/0/YouTube/Music/')
        os.makedirs(output_dir, exist_ok=True)
        print(TextStyles.success(f"Output directory: {output_dir}"))
        with Spinner("Fetching video information..."):
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'force_generic_extractor': True,
                'user_agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/91.0.4472.124 Safari/537.36'),
                'cookiefile': '/storage/emulated/0/YouTube/Cookies/cookies.txt'
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = sanitize_title(info['title'])
                duration = info['duration']
                uploader = info.get('uploader', 'Unknown Artist')
                upload_date = info.get('upload_date', '')
                year = upload_date[:4] if upload_date else ''
        end_time = duration - end_skip_seconds
        if end_time <= start_seconds:
            raise ValueError("End time must be greater than start time")
        audio_temp = os.path.join(output_dir, f'temp_{title}.opus')
        progress_logger = ProgressLogger()
        ydl_audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': audio_temp.replace('.opus', ''),
            'writethumbnail': True,
            'keepvideo': False,
            'addmetadata': True,
            'quiet': True,
            'progress_hooks': [progress_logger.hook],
            'user_agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/91.0.4472.124 Safari/537.36'),
            'cookiefile': '/storage/emulated/0/YouTube/Cookies/cookies.txt',
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'opus',
                    'preferredquality': '192',
                },
                {'key': 'FFmpegMetadata'}
            ],
        }
        with YoutubeDL(ydl_audio_opts) as ydl:
            print(TextStyles.progress("Downloading audio..."))
            ydl.download([url])
        thumbnail_ext = ['webp', 'jpg', 'png']
        thumbnail_path = None
        for ext in thumbnail_ext:
            temp_path = os.path.join(output_dir, f'temp_{title}.{ext}')
            if os.path.exists(temp_path):
                thumbnail_path = temp_path
                break
        if thumbnail_path:
            ext = os.path.splitext(thumbnail_path)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                thumbnail_final = thumbnail_path
            else:
                thumbnail_final = os.path.join(output_dir, f'{title}.jpg')
                with Image.open(thumbnail_path) as img:
                    img.convert('RGB').save(thumbnail_final, 'JPEG')
                os.remove(thumbnail_path)
                print(TextStyles.success("Temporary thumbnail file converted and deleted."))
        else:
            thumbnail_final = None
        print(TextStyles.progress("Trimming audio..."))
        trimmed_audio = os.path.join(output_dir, f'trimmed_{title}.opus')
        trim_command = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-ss', str(start_seconds),
            '-i', audio_temp,
            '-t', str(end_time - start_seconds),
            '-c', 'copy',
            trimmed_audio
        ]
        subprocess.run(trim_command, check=True)
        print(TextStyles.progress("Adding metadata..."))
        final_audio = os.path.join(output_dir, f'{title}.opus')
        if thumbnail_final:
            embed_cover_art_with_opusenc(trimmed_audio, thumbnail_final, final_audio,
                                         title, uploader, year, f"Source={url}")
        else:
            ffmpeg_command = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-i', trimmed_audio,
                '-c', 'copy',
                '-metadata', f'title={title}',
                '-metadata', f'artist={uploader}',
                '-metadata', f'date={year}',
                '-metadata', f'comment=Source={url}',
                final_audio
            ]
            subprocess.run(ffmpeg_command, check=True)
        if os.path.exists(audio_temp):
            os.remove(audio_temp)
            print(TextStyles.success("Temporary audio file deleted."))
        if os.path.exists(trimmed_audio):
            os.remove(trimmed_audio)
            print(TextStyles.success("Trimmed audio file deleted."))
        if thumbnail_final and os.path.exists(thumbnail_final):
            os.remove(thumbnail_final)
            print(TextStyles.success("Thumbnail file deleted."))
        print(TextStyles.success(f"Successfully downloaded:\n{final_audio}"))
    except Exception as e:
        print(TextStyles.fail(f"Error: {str(e)}"))
        exit(1)


def handle_social_media(url, platform):
    try:
        base_dir = os.path.join('/storage/emulated/0/Music/SocialMedia/')
        os.makedirs(base_dir, exist_ok=True)
        next_num = get_next_social_media_number(base_dir)
        final_file = os.path.join(base_dir, f'Social Media Audio {next_num}.opus')
        with Spinner(f"{TextStyles.progress('Fetching webpage...')}"):
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': True,
                'headers': {
                    'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G975F) '
                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                   'Chrome/118.0.5993.169 Mobile Safari/537.36'),
                    'Referer': 'https://www.instagram.com/' if platform == 'Instagram' else 'https://www.google.com/'
                },
                'cookiefile': '/storage/emulated/0/YouTube/Cookies/instagram_cookies.txt' if platform == 'Instagram' else '/storage/emulated/0/YouTube/Cookies/cookies.txt'
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = sanitize_title(info.get('title', 'Unknown Title'), max_length=50)
                uploader = sanitize_title(info.get('uploader', platform), max_length=20)
                upload_date = info.get('upload_date', '')
                year = upload_date[:4] if upload_date else ''
        print(TextStyles.progress("Fetching audio stream..."))
        temp_audio = os.path.join(base_dir, f'temp_{next_num}.opus')
        ydl_audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_audio.replace('.opus', ''),
            'quiet': True,
            'writethumbnail': True,
            'keepvideo': False,
            'addmetadata': True,
            'cookiefile': '/storage/emulated/0/YouTube/Cookies/instagram_cookies.txt' if platform == 'Instagram' else '/storage/emulated/0/YouTube/Cookies/cookies.txt',
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'opus',
                    'preferredquality': '192',
                },
                {'key': 'FFmpegMetadata'}
            ],
        }
        with Spinner("Downloading audio..."):
            with YoutubeDL(ydl_audio_opts) as ydl:
                ydl.download([url])
        thumbnail_ext = ['webp', 'jpg', 'png']
        thumbnail_path = None
        for ext in thumbnail_ext:
            temp_path = os.path.join(base_dir, f'temp_{next_num}.{ext}')
            if os.path.exists(temp_path):
                thumbnail_path = temp_path
                break
        if thumbnail_path:
            ext = os.path.splitext(thumbnail_path)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                thumbnail_final = thumbnail_path
            else:
                thumbnail_final = os.path.join(base_dir, f'thumb_{next_num}.jpg')
                with Image.open(thumbnail_path) as img:
                    img.convert('RGB').save(thumbnail_final, 'JPEG')
                os.remove(thumbnail_path)
                print(TextStyles.success("Temporary thumbnail file converted and deleted."))
        else:
            thumbnail_final = None
        print(TextStyles.progress("Converting to Opus..."))
        if thumbnail_final:
            embed_cover_art_with_opusenc(temp_audio, thumbnail_final, final_file,
                                         title, uploader, year, f"Source={url}")
        else:
            ffmpeg_command = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-i', temp_audio,
                '-c', 'copy',
                '-metadata', f'title={title}',
                '-metadata', f'artist={uploader}',
                '-metadata', f'date={year}',
                '-metadata', f'comment=Source={url}',
                final_file
            ]
            subprocess.run(ffmpeg_command, check=True)
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
            print(TextStyles.success("Temporary audio file deleted."))
        if thumbnail_final and os.path.exists(thumbnail_final):
            os.remove(thumbnail_final)
            print(TextStyles.success("Thumbnail file deleted."))
        print(TextStyles.success(f"Successfully downloaded:\n{final_file}"))
    except Exception as e:
        print(TextStyles.fail(f"Error: {str(e)}"))
        exit(1)


def main():
    # Prompt for URL and detect platform early for faster load
    url = input(TextStyles.input_prompt("Enter URL (YouTube/Facebook/Instagram): ")).strip()
    if not url:
        print(TextStyles.fail("Invalid URL"))
        return
    platform = detect_platform(url)
    print(TextStyles.success(f"Detected platform: {platform}"))
    
    # If YouTube, also prompt for start and end times
    if platform == 'YouTube':
        print(TextStyles.header("YouTube Audio Downloader"))
        start_time = input(TextStyles.input_prompt("Start time [M:SS or SS] (Enter for 0): ")).strip() or '0'
        end_skip = input(TextStyles.input_prompt("Seconds to skip from end [M:SS or SS] (Enter for 0): ")).strip() or '0'
        start_seconds = time_to_seconds(start_time)
        end_skip_seconds = time_to_seconds(end_skip)
    
    # Now import heavy libraries
    import os
    import re
    import sys
    import time
    import threading
    import subprocess
    from tqdm import tqdm
    from PIL import Image
    from yt_dlp import YoutubeDL

    globals()['os'] = os
    globals()['re'] = re
    globals()['sys'] = sys
    globals()['time'] = time
    globals()['threading'] = threading
    globals()['subprocess'] = subprocess
    globals()['tqdm'] = tqdm
    globals()['Image'] = Image
    globals()['YoutubeDL'] = YoutubeDL

    if platform == 'YouTube':
        handle_youtube(url, start_seconds, end_skip_seconds)
    elif platform in ['Facebook', 'Instagram']:
        handle_social_media(url, platform)
    else:
        print(TextStyles.fail("Unsupported platform"))
        return


if __name__ == '__main__':
    main()