import asyncio
from emotion_bot.bot import send_daily_reminder, init_db, close_db
from dotenv import load_dotenv
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    try:
        logger.info("Starting reminder script...")
        await init_db()
        await send_daily_reminder()
    except Exception as e:
        logger.error(f"Error in reminder script: {e}")
    finally:
        await close_db()
        logger.info("Reminder script finished.")

if __name__ == "__main__":
    asyncio.run(main()) 