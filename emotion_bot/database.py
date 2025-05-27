import asyncpg
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

# Получаем URL подключения из Railway
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_pool():
    if DATABASE_URL:
        # Парсим URL подключения
        url = urlparse(DATABASE_URL)
        # Создаем пул соединений
        return await asyncpg.create_pool(
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:],  # Убираем первый слеш из пути
            ssl='require'  # Railway требует SSL
        )
    else:
        # Для локальной разработки
        return await asyncpg.create_pool(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "emotion_bot")
        )

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Создаем таблицу пользователей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                gender TEXT NOT NULL
            )
        ''')
        
        # Создаем таблицу записей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id BIGINT REFERENCES users(user_id),
                hunger_before INTEGER,
                satiety_after INTEGER,
                emotion TEXT,
                sleep_hours REAL,
                location TEXT,
                company TEXT,
                phone TEXT,
                cycle_day INTEGER,
                binge_eating TEXT
            )
        ''')
    await pool.close()

async def get_user(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            'SELECT name, gender FROM users WHERE user_id = $1',
            user_id
        )
    await pool.close()

async def save_user(user_id: int, name: str, gender: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, name, gender)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE 
            SET name = $2, gender = $3
        ''', user_id, name, gender)
    await pool.close()

async def insert_entry(user_id: int, data: dict):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO entries (
                user_id, hunger_before, satiety_after, emotion, 
                sleep_hours, location, company, phone, 
                cycle_day, binge_eating
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ''', (
            user_id,
            data["hunger_before"],
            data["satiety_after"],
            data["emotion"],
            data["sleep_hours"],
            data["location"],
            data["company"],
            data["phone"],
            data.get("cycle_day"),
            data["binge_eating"]
        ))
    await pool.close()
