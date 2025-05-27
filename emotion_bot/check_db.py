import aiosqlite
import asyncio

async def main():
    async with aiosqlite.connect("emotion_data.db") as db:
        print("Users:")
        async with db.execute("SELECT * FROM users") as cursor:
            async for row in cursor:
                print(row)
        print("\nEntries:")
        async with db.execute("SELECT * FROM entries") as cursor:
            async for row in cursor:
                print(row)

if __name__ == "__main__":
    asyncio.run(main()) 