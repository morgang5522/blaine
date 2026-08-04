import os
import subprocess
import logging
from typing import Optional, Callable
from src.config import settings

logger = logging.getLogger("blaine.pipeline.cloud_sync")

class CloudSyncPipeline:
    """
    Rclone-backed sync engine supporting MEGA (S3 Compatible) and Google Drive remotes.
    """
    def __init__(self, rclone_config_path: Optional[str] = None):
        self.rclone_config_path = rclone_config_path

    def sync(
        self,
        local_path: str,
        target_remote: str = "mega", # "mega" or "gdrive"
        subfolder: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file/directory does not exist: {local_path}")

        # Resolve remote target from settings
        if target_remote.lower() == "gdrive":
            remote_base = settings.GDRIVE_REMOTE
        else:
            remote_base = settings.MEGA_S3_REMOTE

        remote_dest = f"{remote_base}/{subfolder.strip('/')}" if subfolder else remote_base

        cmd = ["rclone", "copy", local_path, remote_dest, "--transfers", "4", "--checkers", "8", "--fast-list", "--stats", "1s", "-v"]

        if self.rclone_config_path:
            cmd.extend(["--config", self.rclone_config_path])

        logger.info(f"Syncing '{local_path}' -> '{remote_dest}' via Rclone...")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in iter(process.stdout.readline, ''):
                line_str = line.strip()
                if line_str:
                    if progress_callback and ("Transferred:" in line_str or "%" in line_str):
                        progress_callback(line_str)
            process.wait()
            if process.returncode == 0:
                logger.info(f"Successfully synced '{local_path}' to '{remote_dest}'.")
                return True
            else:
                logger.error(f"Rclone copy process exited with code {process.returncode}")
                return False
        except FileNotFoundError:
            logger.error("Rclone binary not found. Please install rclone.")
            return False
