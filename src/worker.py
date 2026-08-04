import html
import json
import logging
import asyncio
from typing import Dict, Any, Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from src.config import settings
from src.pipeline.archiver import ArchiverPipeline
from src.pipeline.organizer import OrganizerPipeline
from src.pipeline.cloud_sync import CloudSyncPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("blaine.worker")

class BlaineWorker:
    def __init__(self):
        self.archiver = ArchiverPipeline(download_dir=settings.SCRATCH_DIR)
        self.organizer = OrganizerPipeline(base_output_dir=settings.ORGANIZED_DIR)
        self.cloud_sync = CloudSyncPipeline()
        self.redis = None

    async def connect_redis(self):
        if aioredis is None:
            logger.warning("redis-py package missing. Worker running in standalone demo mode.")
            return

        try:
            self.redis = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                socket_timeout=30.0,
                socket_connect_timeout=5.0,
                socket_keepalive=True,
                retry_on_timeout=True
            )
            await self.redis.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Could not connect to Redis ({e}). Retrying in loop.")

    async def notify_telegram(self, chat_id: Optional[int], text: str):
        if not chat_id or not settings.TELEGRAM_BOT_TOKEN:
            return
        try:
            from telegram import Bot
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            logger.info(f"Sent Telegram notification for chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification to chat {chat_id}: {e}")

    async def process_job(self, job_data: Dict[str, Any]):
        job_id = job_data.get("job_id")
        chat_id = job_data.get("chat_id")
        payload = job_data.get("payload", {})
        url = payload.get("url")
        quality = payload.get("quality", "best")
        category = payload.get("category", "General")
        cloud_target = payload.get("cloud_target", "mega")

        logger.info(f"Processing Job [{job_id}]: URL={url}, Category={category}, Target={cloud_target}")

        try:
            # Step 1: Download
            meta = self.archiver.download_media(url, quality_preset=quality)
            
            # Step 2: Organize
            organized_file = self.organizer.organize_file(meta["file_path"], meta, category=category)
            meta["organized_path"] = organized_file

            # Step 3: Cloud Sync
            cloud_status_text = ""
            if cloud_target and cloud_target != "none":
                success = self.cloud_sync.sync(organized_file, target_remote=cloud_target, subfolder=category)
                meta["cloud_sync"] = "SUCCESS" if success else "FAILED"
                cloud_status_text = f"\n☁️ <b>Cloud Sync ({html.escape(str(cloud_target))}):</b> {'✅ Uploaded' if success else '❌ Failed'}"

            logger.info(f"Completed Job [{job_id}]!")

            title = meta.get("title", "Media")
            uploader = meta.get("uploader", "Unknown Uploader")
            duration_secs = meta.get("duration", 0)
            mins, secs = divmod(int(duration_secs), 60)
            duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"

            msg = (
                f"✅ <b>Archiving Complete!</b> (Job <code>{html.escape(str(job_id))}</code>)\n\n"
                f"🎬 <b>Title:</b> {html.escape(title)}\n"
                f"👤 <b>Uploader:</b> {html.escape(uploader)}\n"
                f"⏱ <b>Duration:</b> {duration_str}\n"
                f"📁 <b>Category:</b> {html.escape(category)}"
                f"{cloud_status_text}"
            )
            await self.notify_telegram(chat_id, msg)
            return meta
        except Exception as e:
            logger.exception(f"Job [{job_id}] failed with error: {e}")
            err_summary = str(e)
            msg = (
                f"❌ <b>Archiving Failed</b> (Job <code>{html.escape(str(job_id))}</code>)\n\n"
                f"<b>Error:</b> <code>{html.escape(err_summary)}</code>"
            )
            await self.notify_telegram(chat_id, msg)
            raise

    async def run(self):
        await self.connect_redis()
        logger.info("Blaine Task Worker is online and waiting for jobs...")
        
        while True:
            try:
                if self.redis:
                    res = await self.redis.blpop("blaine_jobs", timeout=5)
                    if res:
                        _, item = res
                        job_data = json.loads(item)
                        await self.process_job(job_data)
                else:
                    await asyncio.sleep(5)
            except (asyncio.TimeoutError, Exception) as e:
                err_msg = str(e)
                # Ignore normal idle blpop read timeouts
                if "Timeout reading from" in err_msg or isinstance(e, asyncio.TimeoutError):
                    continue
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(2)


if __name__ == "__main__":
    worker = BlaineWorker()
    asyncio.run(worker.run())
