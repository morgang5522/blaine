import sys
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("blaine.main")

def run():
    mode = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if mode == "worker":
        logger.info("Starting Blaine Task Worker...")
        from src.worker import BlaineWorker
        worker = BlaineWorker()
        asyncio.run(worker.run())
    else:
        logger.info("Starting Blaine Telegram Bot...")
        from src.bot import main as bot_main
        bot_main()

if __name__ == "__main__":
    run()
