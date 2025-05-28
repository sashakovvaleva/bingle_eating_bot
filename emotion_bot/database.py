# emotion_bot/database.py

import asyncpg
import asyncio
import ssl
import os
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

url = urlparse(DATABASE_URL)

# SSL конфигурация для Railway PostgreSQL
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

_pool = None  # глобальный пул соединений

async def init_db():
    """Инициализация базы данных и создание пула соединений"""
    logger.info("Initializing database...")
    global _pool
    
    if _pool is None:
        try:
            # Создаем пул соединений
            _pool = await asyncpg.create_pool(
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port,
                database=url.path[1:],
                ssl=ssl_context,
                min_size=1,      # Минимум соединений
                max_size=10,     # Максимум соединений
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Отключаем JIT для стабильности
                }
            )
            logger.info("Database pool created successfully")
            
            # Создаем таблицы
            await create_tables()
            logger.info("Database initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    else:
        logger.info("Database already initialized")

async def get_pool():
    """Получение пула соединений"""
    if _pool is None:
        logger.error("Database not initialized. Call init_db() first.")
        raise RuntimeError("Database not initialized")
    return _pool

async def create_tables():
    """Создание таблиц в базе данных"""
    logger.info("Creating database tables...")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            # Создаем таблицу пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    gender TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Создаем таблицу записей
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
                    binge_eating TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Создаем таблицу для дней цикла
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cycle_days (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    cycle_day INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Создаем индексы для оптимизации
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_user_id ON entries(user_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cycle_days_user_id ON cycle_days(user_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cycle_days_created_at ON cycle_days(created_at);
            """)
            
            logger.info("Tables created successfully")
            
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

async def get_user(user_id):
    """Получение данных пользователя"""
    logger.info(f"Getting user data for user_id: {user_id}")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT name, gender FROM users WHERE id = $1", user_id)
            if row:
                logger.info(f"User found: {row['name']}, {row['gender']}")
                return (row["name"], row["gender"])
            else:
                logger.info(f"No user found for user_id: {user_id}")
                return None
                
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

async def save_user(user_id, name, gender):
    """Сохранение пользователя"""
    logger.info(f"Saving user: id={user_id}, name={name}, gender={gender}")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, name, gender)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET 
                    name = EXCLUDED.name, 
                    gender = EXCLUDED.gender;
            """, user_id, name, gender)
            logger.info("User saved successfully")
            
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        raise

async def insert_entry(user_id, data):
    """Вставка записи о приеме пищи"""
    logger.info(f"Inserting entry for user_id: {user_id}")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO entries (
                    user_id, hunger_before, satiety_after, emotion,
                    sleep_hours, location, company, phone, binge_eating
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
                user_id,
                data.get("hunger_before"),
                data.get("satiety_after"),
                data.get("emotion"),
                data.get("sleep_hours"),
                data.get("location"),
                data.get("company"),
                data.get("phone"),
                data.get("binge_eating")
            )
            logger.info("Entry inserted successfully")
            
    except Exception as e:
        logger.error(f"Error inserting entry: {e}")
        raise

async def get_user_entries(user_id, limit=10):
    """Получение записей пользователя"""
    logger.info(f"Getting entries for user_id: {user_id}")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM entries 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, user_id, limit)
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Error getting user entries: {e}")
        return []

async def get_last_cycle_day(user_id):
    """Получение последнего дня цикла пользователя"""
    logger.info(f"Getting last cycle day for user_id: {user_id}")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT cycle_day 
                FROM cycle_days 
                WHERE user_id = $1 
                AND DATE(created_at) = CURRENT_DATE
                ORDER BY created_at DESC 
                LIMIT 1
            """, user_id)
            return row['cycle_day'] if row else None
            
    except Exception as e:
        logger.error(f"Error getting last cycle day: {e}")
        return None

async def save_cycle_day(user_id, cycle_day):
    """Сохранение дня цикла"""
    logger.info(f"Saving cycle day for user_id: {user_id}")
    pool = await get_pool()
    
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cycle_days (user_id, cycle_day)
                VALUES ($1, $2)
            """, user_id, cycle_day)
            logger.info("Cycle day saved successfully")
            
    except Exception as e:
        logger.error(f"Error saving cycle day: {e}")
        raise

async def close_db():
    """Закрытие пула соединений (вызывается при завершении приложения)"""
    global _pool
    if _pool:
        logger.info("Closing database pool...")
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")

# Функция для тестирования подключения
async def test_connection():
    """Тестирование подключения к базе данных"""
    try:
        await init_db()
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            logger.info(f"Database connection test successful: {result}")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Тест подключения
    asyncio.run(test_connection())