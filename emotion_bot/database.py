# emotion_bot/database.py

import asyncpg
import ssl
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

url = urlparse(DATABASE_URL)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

_pool = None  # глобальный пул соединений

async def init_db():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:],
            ssl=ssl_context
        )
        await create_tables()

async def get_pool():
    if _pool is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _pool

async def create_tables():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                gender TEXT
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                hunger_before INTEGER,
                satiety_after INTEGER,
                emotion TEXT,
                sleep_hours FLOAT,
                location TEXT,
                company TEXT,
                phone TEXT,
                cycle_day INTEGER,
                binge_eating TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

async def get_user(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT name, gender FROM users WHERE id = $1", user_id)
        return (row["name"], row["gender"]) if row else None

async def save_user(user_id, name, gender):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, name, gender)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, gender = EXCLUDED.gender;
        """, user_id, name, gender)

async def insert_entry(user_id, data):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO entries (
                user_id, hunger_before, satiety_after, emotion,
                sleep_hours, location, company, phone, cycle_day, binge_eating
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, user_id,
            data.get("hunger_before"),
            data.get("satiety_after"),
            data.get("emotion"),
            data.get("sleep_hours"),
            data.get("location"),
            data.get("company"),
            data.get("phone"),
            data.get("cycle_day"),
            data.get("binge_eating")
        )
