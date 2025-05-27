import asyncpg
import asyncio
import ssl
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

async def main():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("DATABASE_URL not found in env")
        return

    url = urlparse(DATABASE_URL)
    print(f"Connecting to DB at {url.hostname}:{url.port} as {url.username}")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    pool = await asyncpg.create_pool(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        database=url.path[1:],
        ssl=ssl_context
    )

    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users")
        print(users)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
