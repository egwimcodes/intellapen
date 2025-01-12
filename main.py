from yt_dlp import YoutubeDL

url = "https://www.youtube.com/watch?v=yoCfT88Fo6c"
with YoutubeDL() as ydl:
    info = ydl.extract_info(url, download=False)
    print(f"Title {info['title']}")
