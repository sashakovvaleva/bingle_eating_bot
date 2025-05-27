import asyncpg
import asyncio
import os
import pandas as pd
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

async def main():
    # Получаем URL подключения из Railway
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found in environment variables")
        return

    # Парсим URL подключения
    url = urlparse(DATABASE_URL)
    
    # Создаем пул соединений
    pool = await asyncpg.create_pool(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        database=url.path[1:],  # Убираем первый слеш из пути
        ssl='require'  # Railway требует SSL
    )

    async with pool.acquire() as conn:
        # Получаем данные пользователей
        users = await conn.fetch("SELECT * FROM users")
        users_df = pd.DataFrame(users)
        print("\nUsers DataFrame:")
        print(users_df)
        print("\nUsers DataFrame Info:")
        print(users_df.info())

        # Получаем данные записей
        entries = await conn.fetch("""
            SELECT e.*, u.name 
            FROM entries e 
            JOIN users u ON e.user_id = u.user_id 
            ORDER BY e.timestamp DESC
        """)
        entries_df = pd.DataFrame(entries)
        print("\nEntries DataFrame:")
        print(entries_df)
        print("\nEntries DataFrame Info:")
        print(entries_df.info())

        # Сохраняем в CSV файлы
        users_df.to_csv('users_data.csv', index=False)
        entries_df.to_csv('entries_data.csv', index=False)
        print("\nData saved to CSV files: users_data.csv and entries_data.csv")

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main()) 