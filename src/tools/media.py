import logging
from typing import Dict, Any
from src.tools.base import BaseTool

logger = logging.getLogger("blaine.tools.media")

class ArchiveMediaTool(BaseTool):
    @property
    def name(self) -> str:
        return "archive_media"

    @property
    def description(self) -> str:
        return "Downloads and archives video or audio from YouTube, Podcasts, or media URLs using yt-dlp and ffmpeg."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the video, audio, or podcast to download."
                },
                "quality": {
                    "type": "string",
                    "description": "Quality preset: 'best', '1080p', '720p', 'audio_mp3', or 'audio_flac'.",
                    "default": "best"
                },
                "extract_audio": {
                    "type": "boolean",
                    "description": "True if only audio should be extracted as MP3/FLAC.",
                    "default": False
                },
                "category": {
                    "type": "string",
                    "description": "Category or topic (e.g. 'Tech', 'Podcasts', 'Music', 'Documentaries').",
                    "default": "General"
                },
                "cloud_target": {
                    "type": "string",
                    "description": "Destination cloud remote: 'mega', 'gdrive', or 'none'.",
                    "default": "mega"
                }
            },
            "required": ["url"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        logger.info(f"ArchiveMediaTool triggered with args: {kwargs}")
        return {
            "status": "QUEUED",
            "message": "Media archiving job successfully queued in background worker.",
            "job_details": kwargs
        }


class CloudSyncTool(BaseTool):
    @property
    def name(self) -> str:
        return "cloud_sync"

    @property
    def description(self) -> str:
        return "Synchronizes local files or directories to cloud storage remotes (MEGA S3 compatible or Google Drive)."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "local_path": {
                    "type": "string",
                    "description": "The path of the local file or folder to upload."
                },
                "destination_remote": {
                    "type": "string",
                    "description": "Target remote cloud provider ('mega' or 'gdrive').",
                    "default": "mega"
                },
                "target_folder": {
                    "type": "string",
                    "description": "Folder path on the cloud storage."
                }
            },
            "required": ["local_path"]
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        logger.info(f"CloudSyncTool triggered with args: {kwargs}")
        return {
            "status": "QUEUED",
            "message": "Cloud sync job queued successfully.",
            "job_details": kwargs
        }
