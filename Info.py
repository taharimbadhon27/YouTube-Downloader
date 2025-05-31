import os
import re

# Configuration
API_KEY_FILE = os.path.expanduser("~/.youtube_api_key")
OUTPUT_DIR = "/storage/emulated/0/YouTube/INFO/"
FONT_PATH = "/storage/emulated/0/YouTube/Cookies/NotoSansBengali-Regular.ttf"

def get_api_key():
    """Get API key from storage or prompt user once."""
    try:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, 'r') as f:
                return f.read().strip()
        else:
            api_key = "AIzaSyBnyZmnPQpL5_kZUFiR14a9wP5FgVyS8cQ"  # Your provided key
            with open(API_KEY_FILE, 'w') as f:
                f.write(api_key)
            return api_key
    except Exception as e:
        print(f"Error handling API key: {str(e)}")
        exit(1)

def sanitize_filename(title):
    """Sanitize the title to make it a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', '_', title).strip()

# Functions that depend on heavy libraries (requests, weasyprint, yt_dlp)
# Their definitions remain unchanged; we assume these modules will be imported later.

def get_channel_info(api_key, channel_id):
    """Get channel title using channel ID."""
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={api_key}"
    response = requests.get(url).json()
    if response.get('items'):
        return response['items'][0]['snippet']['title']
    return "Unknown_Channel"

def get_channel_id(api_key, url):
    """Extract channel ID from the given URL."""
    if '/channel/' in url:
        return url.split('/channel/')[-1].split('/')[0]
    elif '/@' in url:
        handle = url.split('/@')[-1].split('/')[0]
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=channel&q={handle}&key={api_key}"
        response = requests.get(search_url).json()
        if response.get('items'):
            return response['items'][0]['snippet']['channelId']
    return None

def get_playlists(api_key, channel_id):
    """Fetch all playlists for a given channel ID using the API."""
    playlists = []
    next_page_token = None

    while True:
        url = f"https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId={channel_id}&maxResults=50&key={api_key}"
        if next_page_token:
            url += f"&pageToken={next_page_token}"
        
        response = requests.get(url).json()
        playlists.extend(response.get('items', []))
        next_page_token = response.get('nextPageToken')
        if not next_page_token: 
            break

    return playlists

def get_videos_ytdlp(channel_url):
    """
    Fetch all videos from the channel using yt-dlp.
    To avoid extracting unwanted tabs (like streams), we append '/videos' if not already present.
    The options below suppress progress messages.
    """
    if not channel_url.rstrip("/").endswith("/videos"):
        channel_url = channel_url.rstrip("/") + "/videos"
    
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        videos = info.get('entries', [])
        return videos

def generate_html(channel_title, playlists, videos):
    """Generate an HTML string with channel, playlists, and videos info, applying the custom font."""
    css = f"""
    <style>
    @font-face {{
        font-family: 'NotoSansBengali';
        src: url('file://{FONT_PATH}');
    }}
    body {{
        font-family: 'NotoSansBengali', sans-serif;
        margin: 2em;
        line-height: 1.6;
    }}
    h1 {{
        font-size: 2em;
        margin-bottom: 0.5em;
    }}
    h2 {{
        font-size: 1.5em;
        margin-top: 1.5em;
    }}
    a {{
        color: #0645AD;
        text-decoration: none;
    }}
    a:hover {{
        text-decoration: underline;
    }}
    </style>
    """

    html = f"""<html>
<head>
<meta charset="UTF-8">
{css}
<title>{channel_title} Info</title>
</head>
<body>
<h1>Channel: {channel_title}</h1>
"""

    # Playlists section (using API)
    html += "<h2>Playlists</h2>\n"
    if playlists:
        html += "<ol>\n"
        for playlist in playlists:
            title = playlist['snippet']['title']
            playlist_id = playlist['id']
            playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            html += f"<li><a href='{playlist_url}' target='_blank'>{title}</a></li>\n"
        html += "</ol>\n"
    else:
        html += "<p>No playlists found.</p>\n"

    # Videos section (using yt-dlp)
    html += "<h2>Videos</h2>\n"
    if videos:
        html += "<ol>\n"
        for video in videos:
            video_id = video.get('id')
            title = video.get('title', 'No Title')
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            html += f"<li><a href='{video_url}' target='_blank'>{title}</a></li>\n"
        html += "</ol>\n"
    else:
        html += "<p>No videos found.</p>\n"

    html += """
</body>
</html>
"""
    return html

def main():
    # Setup environment
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get channel URL from user (fast-loading part)
    channel_url = input("Enter YouTube Channel URL: ").strip()
    
    # Heavy imports moved here
    global requests, HTML, yt_dlp
    import requests
    from weasyprint import HTML
    import yt_dlp

    # Get API key (automatically handled)
    api_key = get_api_key()

    # Get channel ID (for API calls)
    channel_id = get_channel_id(api_key, channel_url)
    if not channel_id:
        print("❌ Could not extract channel ID from URL")
        return

    # Get channel info using API
    channel_title = get_channel_info(api_key, channel_id)
    sanitized_title = sanitize_filename(channel_title)

    # Fetch playlists using API
    playlists = get_playlists(api_key, channel_id)

    # Fetch videos using yt-dlp (to save API quota)
    videos = get_videos_ytdlp(channel_url)

    if not playlists and not videos:
        print("ℹ️ No playlists or videos found for this channel")
        return

    # Generate HTML content from channel info, playlists, and videos
    html_content = generate_html(channel_title, playlists, videos)
    
    # Create output file with .pdf extension
    filename = f"{sanitized_title}_Info.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Convert HTML to PDF using WeasyPrint
    HTML(string=html_content).write_pdf(filepath)

    print(f"\n✅ Successfully saved channel info with {len(playlists)} playlists and {len(videos)} videos to PDF:")
    print(f"📁 {filepath}")

if __name__ == "__main__":
    main()