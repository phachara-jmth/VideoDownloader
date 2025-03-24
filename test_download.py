import yt_dlp

video_page_url = "https://ok.ru/video/9810646141687"
#video_page_url = "https://krussdomi.com/vidstreaming/player.php?id=67cc57f1169c31976bc4497d&ln=ja-JP"

ydl_opts = {
    'outtmpl': 'anime_video.mp4',
    'format': 'best'
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([video_page_url])
