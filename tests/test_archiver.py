import unittest
import os
import tempfile
import sys
from unittest.mock import MagicMock

if "yt_dlp" not in sys.modules:
    mock_ytdlp_module = MagicMock()
    sys.modules["yt_dlp"] = mock_ytdlp_module

import src.pipeline.archiver as archiver_module
from src.pipeline.archiver import ArchiverPipeline

class TestArchiverPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pipeline = ArchiverPipeline(download_dir=self.tmp_dir.name)
        archiver_module.yt_dlp = sys.modules["yt_dlp"]
        archiver_module.yt_dlp.YoutubeDL.side_effect = None

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_get_cookies_path_custom(self):
        cookie_file = os.path.join(self.tmp_dir.name, "my_cookies.txt")
        with open(cookie_file, "w") as f:
            f.write("# Netscape HTTP Cookie File")
        
        pipeline = ArchiverPipeline(download_dir=self.tmp_dir.name, cookies_path=cookie_file)
        self.assertEqual(pipeline._get_cookies_path(), cookie_file)

    def test_build_ydl_opts_includes_headers_and_extractor_args(self):
        opts = self.pipeline._build_ydl_opts(
            out_tmpl="test_tmpl",
            quality_preset="1080p",
            extract_audio=False,
            player_clients=['android', 'ios']
        )
        
        self.assertIn('http_headers', opts)
        self.assertIn('User-Agent', opts['http_headers'])
        self.assertIn('extractor_args', opts)
        self.assertEqual(opts['extractor_args']['youtube']['player_client'], ['android', 'ios'])
        self.assertEqual(opts.get('merge_output_format'), 'mp4')

    def test_build_ydl_opts_with_cookies_file(self):
        cookie_file = os.path.join(self.tmp_dir.name, "cookies.txt")
        with open(cookie_file, "w") as f:
            f.write("cookie data")

        pipeline = ArchiverPipeline(download_dir=self.tmp_dir.name, cookies_path=cookie_file)
        opts = pipeline._build_ydl_opts(
            out_tmpl="test_tmpl",
            quality_preset="best",
            extract_audio=False
        )

        self.assertEqual(opts.get('cookiefile'), cookie_file)

    def test_download_media_success(self):
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {
            "title": "Test Video",
            "uploader": "Test Channel",
            "upload_date": "20260804",
            "duration": 120,
            "description": "Test description",
            "id": "12345",
            "webpage_url": "https://youtube.com/watch?v=12345"
        }
        mock_ydl_instance.prepare_filename.return_value = os.path.join(self.tmp_dir.name, "Test Video [12345].mp4")

        mock_ydl_cls = sys.modules["yt_dlp"].YoutubeDL
        mock_ydl_cls.side_effect = None
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        meta = self.pipeline.download_media("https://youtube.com/watch?v=12345")
        self.assertEqual(meta["title"], "Test Video")
        self.assertEqual(meta["id"], "12345")

    def test_download_media_bot_detection_fallback(self):
        instance_fail = MagicMock()
        instance_fail.extract_info.side_effect = Exception("Sign in to confirm you’re not a bot.")
        
        instance_success = MagicMock()
        instance_success.extract_info.return_value = {
            "title": "Fallback Video",
            "id": "abc"
        }
        instance_success.prepare_filename.return_value = os.path.join(self.tmp_dir.name, "Fallback Video [abc].mp4")

        mock_ydl_cls = sys.modules["yt_dlp"].YoutubeDL
        mock_ydl_cls.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=instance_fail)),
            MagicMock(__enter__=MagicMock(return_value=instance_fail)),
            MagicMock(__enter__=MagicMock(return_value=instance_success)),
        ]

        meta = self.pipeline.download_media("https://youtube.com/watch?v=abc")
        self.assertEqual(meta["title"], "Fallback Video")

if __name__ == "__main__":
    unittest.main()
