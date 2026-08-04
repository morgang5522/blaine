import os
import logging
from typing import Callable, Optional, Dict, Any, List

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

logger = logging.getLogger("blaine.pipeline.archiver")

class ArchiverPipeline:
    def __init__(self, download_dir: str = "/var/blaine/scratch", cookies_path: Optional[str] = None):
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)
        self.cookies_path = cookies_path

    def _get_cookies_path(self) -> Optional[str]:
        if self.cookies_path and os.path.exists(self.cookies_path):
            return self.cookies_path

        try:
            from src.config import settings
            env_path = getattr(settings, "YTDLP_COOKIES_PATH", None) or os.getenv("YTDLP_COOKIES_PATH")
            if env_path and os.path.exists(env_path):
                return env_path
        except ImportError:
            pass

        for candidate in ["/var/blaine/cookies.txt", "data/cookies.txt", "cookies.txt"]:
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

        return None

    def _build_ydl_opts(
        self,
        out_tmpl: str,
        quality_preset: str,
        extract_audio: bool,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        player_clients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        ydl_opts = {
            'outtmpl': out_tmpl,
            'merge_output_format': 'mp4',
            'writethumbnail': True,
            'writeinfojson': True,
            'writesubtitles': True,
            'subtitleslangs': ['en'],
            'concurrent_fragment_downloads': 4,
            'postprocessors': [
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
            ],
            'quiet': False,
            'no_warnings': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        clients = player_clients or ['android', 'ios', 'mweb', 'web']
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': clients,
            }
        }

        cookies_file = self._get_cookies_path()
        if cookies_file:
            logger.info(f"Using yt-dlp cookies from file: {cookies_file}")
            ydl_opts['cookiefile'] = cookies_file
        else:
            try:
                from src.config import settings
                cookies_browser = getattr(settings, "YTDLP_COOKIES_FROM_BROWSER", None) or os.getenv("YTDLP_COOKIES_FROM_BROWSER")
                if cookies_browser:
                    logger.info(f"Using yt-dlp cookies from browser: {cookies_browser}")
                    ydl_opts['cookiesfrombrowser'] = (cookies_browser,)
            except ImportError:
                pass

        if progress_callback:
            def internal_hook(d):
                if d.get('status') == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    speed = d.get('speed', 0)
                    percent = (downloaded / total * 100) if total > 0 else 0
                    progress_callback({
                        "percent": round(percent, 1),
                        "downloaded_bytes": downloaded,
                        "total_bytes": total,
                        "speed": speed,
                        "eta": d.get('eta', 0)
                    })
            ydl_opts['progress_hooks'] = [internal_hook]

        if extract_audio or (quality_preset and quality_preset.startswith("audio")):
            ydl_opts['format'] = 'bestaudio/best'
            codec = 'mp3' if quality_preset == "audio_mp3" else 'flac'
            ydl_opts['postprocessors'].insert(0, {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': '192',
            })

        return ydl_opts

    def download_media(
        self,
        url: str,
        quality_preset: str = "best",
        extract_audio: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Downloads media using yt-dlp & ffmpeg.
        """
        if yt_dlp is None:
            raise RuntimeError("yt-dlp is not installed in the python environment.")

        out_tmpl = os.path.join(self.download_dir, "%(title)s [%(id)s].%(ext)s")

        client_attempts = [
            ['android', 'ios', 'mweb', 'web'],
            ['ios', 'mweb', 'tv_embedded'],
            ['android', 'web_creator'],
        ]

        last_exception = None
        for i, clients in enumerate(client_attempts):
            ydl_opts = self._build_ydl_opts(out_tmpl, quality_preset, extract_audio, progress_callback, player_clients=clients)
            logger.info(f"Downloading '{url}' with quality '{quality_preset}' (Attempt {i+1}, clients={clients})...")

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)

                    if extract_audio or quality_preset.startswith("audio"):
                        base, _ = os.path.splitext(filename)
                        target_ext = '.mp3' if quality_preset == "audio_mp3" else '.flac'
                        if os.path.exists(base + target_ext):
                            filename = base + target_ext

                    return {
                        "file_path": filename,
                        "title": info.get("title", "Untitled"),
                        "uploader": info.get("uploader") or info.get("channel") or "Unknown Uploader",
                        "upload_date": str(info.get("upload_date", "00000000")),
                        "duration": info.get("duration", 0),
                        "description": info.get("description", ""),
                        "id": info.get("id", ""),
                        "webpage_url": info.get("webpage_url", url),
                    }
            except Exception as e:
                err_msg = str(e)
                last_exception = e
                if any(term in err_msg for term in ["Sign in to confirm", "not a bot", "Use --cookies", "Requested format is not available", "format is not available"]):
                    logger.warning(f"YouTube bot detection or format error encountered on attempt {i+1} using clients {clients}: {err_msg}")
                    if i < len(client_attempts) - 1:
                        continue
                else:
                    raise

        if last_exception:
            cookies_file = self._get_cookies_path()
            if not cookies_file:
                raise RuntimeError(
                    f"YouTube requested sign-in / bot authentication: {last_exception}. "
                    "Please provide cookies by placing a valid cookies.txt file at /var/blaine/cookies.txt "
                    "or setting YTDLP_COOKIES_PATH environment variable."
                ) from last_exception
            raise last_exception
