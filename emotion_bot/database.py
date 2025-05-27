import aiosqlite

DB_NAME = "emotion_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                gender TEXT
            )
        ''')
        
        # Создаем таблицу записей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                hunger_before INTEGER,
                satiety_after INTEGER,
                emotion TEXT,
                sleep_hours REAL,
                location TEXT,
                company TEXT,
                phone TEXT,
                cycle_day INTEGER,
                binge_eating TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT name, gender FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def save_user(user_id: int, name: str, gender: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO users (user_id, name, gender)
            VALUES (?, ?, ?)
        ''', (user_id, name, gender))
        await db.commit()

async def insert_entry(user_id: int, data: dict):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO entries (
                user_id, hunger_before, satiety_after, emotion, 
                sleep_hours, location, company, phone, 
                cycle_day, binge_eating
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        await db.commit()
