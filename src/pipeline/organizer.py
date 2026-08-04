import os
import re
import shutil
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("blaine.pipeline.organizer")

class OrganizerPipeline:
    def __init__(self, base_output_dir: str = "/var/blaine/organized"):
        self.base_output_dir = os.path.abspath(base_output_dir)
        os.makedirs(self.base_output_dir, exist_ok=True)

    def sanitize_name(self, text: str) -> str:
        clean = re.sub(r'[\\/*?:"<>|]', "", text)
        clean = clean.strip().replace(" ", "_")
        return clean or "unnamed"

    def organize_file(
        self,
        source_path: str,
        metadata: Dict[str, Any],
        category: Optional[str] = "General",
        template: str = "{category}/{uploader}/{date}_{title}{ext}"
    ) -> str:
        """
        Organizes a file into clean folder hierarchy.
        Returns the absolute destination path.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file not found: {source_path}")

        _, ext = os.path.splitext(source_path)
        uploader = self.sanitize_name(metadata.get("uploader") or "Unknown_Creator")
        title = self.sanitize_name(metadata.get("title") or "Untitled")
        raw_date = str(metadata.get("upload_date") or "00000000")
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else raw_date
        target_category = self.sanitize_name(category or "General")

        rel_path = template.format(
            category=target_category,
            uploader=uploader,
            date=formatted_date,
            title=title,
            ext=ext
        )

        dest_abs_path = os.path.join(self.base_output_dir, rel_path)
        os.makedirs(os.path.dirname(dest_abs_path), exist_ok=True)

        logger.info(f"Organizing file: '{source_path}' -> '{dest_abs_path}'")
        shutil.move(source_path, dest_abs_path)

        # Move sidecar metadata assets if available (.info.json, thumbnail)
        base_src, _ = os.path.splitext(source_path)
        base_dst, _ = os.path.splitext(dest_abs_path)
        for sidecar in ['.info.json', '.jpg', '.png', '.webp', '.vtt', '.srt']:
            if os.path.exists(base_src + sidecar):
                shutil.move(base_src + sidecar, base_dst + sidecar)

        return dest_abs_path
