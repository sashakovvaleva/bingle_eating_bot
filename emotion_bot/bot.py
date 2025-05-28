import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from database import (
    init_db, insert_entry, get_user, save_user, close_db,
    get_last_cycle_day, save_cycle_day, get_pool
)
from dotenv import load_dotenv
import os
import logging
import sys
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class DiaryForm(StatesGroup):
    name = State()
    gender = State()
    hunger_before = State()
    satiety_after = State()
    emotion = State()
    sleep_hours = State()
    location = State()
    company = State()
    phone = State()
    cycle_day = State()
    binge_eating = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    logger.info(f"Start command received from user {message.from_user.id}")
    user = await get_user(message.from_user.id)
    if user:
        name, _ = user
        await message.answer(
            f"Снова здравствуй, {name}!\n\n"
            "Нажми на кнопку ниже, чтобы записать приём пищи 👇",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📝 Записать приём пищи")]],
                resize_keyboard=True
            )
        )
    else:
        await state.set_state(DiaryForm.name)
        await message.answer(
            "Привет! 👋 Введи своё имя:"
        )

@dp.message(lambda message: message.text == "📝 Записать приём пищи")
async def meal_button(message: types.Message, state: FSMContext):
    await meal(message, state)

@dp.message(DiaryForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")]],
        resize_keyboard=True
    )
    await message.answer("Выбери пол:", reply_markup=kb)
    await state.set_state(DiaryForm.gender)

@dp.message(DiaryForm.gender)
async def gender(message: types.Message, state: FSMContext):
    gender = message.text.lower()
    data = await state.get_data()
    await save_user(message.from_user.id, data["name"], gender)
    await state.update_data(gender=gender)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 6)],
            [KeyboardButton(text=str(i)) for i in range(6, 11)]
        ],
        resize_keyboard=True
    )
    await message.answer(f"{data['name']}, от 1 до 10, какой был голод перед едой?", reply_markup=kb)
    await state.set_state(DiaryForm.hunger_before)

@dp.message(Command("meal"))
async def meal(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Давай сначала познакомимся! Как тебя зовут?")
        await state.set_state(DiaryForm.name)
        return
    name, gender = user
    await state.update_data(gender=gender)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 6)],
            [KeyboardButton(text=str(i)) for i in range(6, 11)]
        ],
        resize_keyboard=True
    )
    await message.answer(f"{name}, от 1 до 10, какой был голод перед едой?", reply_markup=kb)
    await state.set_state(DiaryForm.hunger_before)

@dp.message(DiaryForm.hunger_before)
async def hunger_before(message: types.Message, state: FSMContext):
    await state.update_data(hunger_before=int(message.text))
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 6)],
            [KeyboardButton(text=str(i)) for i in range(6, 11)]
        ],
        resize_keyboard=True
    )
    await message.answer("Какой уровень сытости после?", reply_markup=kb)
    await state.set_state(DiaryForm.satiety_after)

@dp.message(DiaryForm.satiety_after)
async def satiety_after(message: types.Message, state: FSMContext):
    await state.update_data(satiety_after=int(message.text))
    emotions = [
        "😐 Нейтрально", "😊 Радость", "😢 Грусть", "😠 Злость", "😰 Тревога",
        "😴 Усталость", "😞 Стыд", "🤯 Стресс", "🥱 Скука", "😍 Вдохновение"
    ]
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=emotion)] for emotion in emotions],
        resize_keyboard=True
    )
    await message.answer("Какая эмоция?", reply_markup=kb)
    await state.set_state(DiaryForm.emotion)

@dp.message(DiaryForm.emotion)
async def emotion(message: types.Message, state: FSMContext):
    await state.update_data(emotion=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=str(i)) for i in range(1, 7)],
            [KeyboardButton(text=str(i)) for i in range(7, 13)]
        ],
        resize_keyboard=True
    )
    await message.answer("Сколько часов ты спал(а)?", reply_markup=kb)
    await state.set_state(DiaryForm.sleep_hours)

@dp.message(DiaryForm.sleep_hours)
async def sleep_hours(message: types.Message, state: FSMContext):
    await state.update_data(sleep_hours=float(message.text))
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Дома"), KeyboardButton(text="💼 Работа")],
            [KeyboardButton(text="🍽️ Кафе"), KeyboardButton(text="🚶 На ходу")]
        ],
        resize_keyboard=True
    )
    await message.answer("Где ты ел(а)?", reply_markup=kb)
    await state.set_state(DiaryForm.location)

@dp.message(DiaryForm.location)
async def location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="один/одна"), KeyboardButton(text="с кем-то")]],
        resize_keyboard=True
    )
    await message.answer("Ты ел(а) один или с кем-то?", reply_markup=kb)
    await state.set_state(DiaryForm.company)

@dp.message(DiaryForm.company)
async def company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="с телефоном"), KeyboardButton(text="без телефона")]],
        resize_keyboard=True
    )
    await message.answer("Ты ел(а) с телефоном или без?", reply_markup=kb)
    await state.set_state(DiaryForm.phone)

@dp.message(DiaryForm.phone)
async def phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    if data["gender"] == "женский":
        cycle_day = await get_last_cycle_day(message.from_user.id)
        if cycle_day is not None:
            await state.update_data(cycle_day=cycle_day)
            await ask_binge(message, state)
        else:
            await message.answer("Какой сегодня день цикла (1-40)?", reply_markup=types.ReplyKeyboardRemove())
            await state.set_state(DiaryForm.cycle_day)
    else:
        await ask_binge(message, state)

@dp.message(DiaryForm.cycle_day)
async def cycle_day(message: types.Message, state: FSMContext):
    await state.update_data(cycle_day=int(message.text))
    await save_cycle_day(message.from_user.id, int(message.text))
    await ask_binge(message, state)

async def ask_binge(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Нет"), KeyboardButton(text="⚠️ Лёгкое переедание")],
            [KeyboardButton(text="❗ Сильное переедание"), KeyboardButton(text="🔥 Срыв")],
        ],
        resize_keyboard=True
    )
    await message.answer("Как ты оцениваешь приём пищи?", reply_markup=kb)
    await state.set_state(DiaryForm.binge_eating)

@dp.message(DiaryForm.binge_eating)
async def binge_eating(message: types.Message, state: FSMContext):
    await state.update_data(binge_eating=message.text)
    data = await state.get_data()
    await insert_entry(message.from_user.id, data)
    user = await get_user(message.from_user.id)
    name = user[0] if user else "Пользователь"
    await message.answer(f"Спасибо, {name}! Всё записано 🙌", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# 🔔 Тестовое напоминание (после 30 сек)
async def send_test_reminder():
    logger.info("🧪 Sending test reminder...")
    try:
        test_user_id = YOUR_TELEGRAM_ID  # <<< ЗАМЕНИ на свой ID
        await bot.send_message(
            test_user_id,
            "🔔 Тестовое напоминание: reminder работает!",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📝 Записать приём пищи")]],
                resize_keyboard=True
            )
        )
        logger.info(f"✅ Test reminder sent to user {test_user_id}")
    except Exception as e:
        logger.error(f"❌ Error sending test reminder: {e}")

async def reminder_task():
    logger.info("🕒 Starting test reminder task (30s delay)...")
    try:
        await asyncio.sleep(30)
        logger.info("⏰ 30s passed — sending test reminder now")
        await send_test_reminder()
    except Exception as e:
        logger.error(f"💥 Exception in reminder_task: {e}")

async def main():
    logger.info("Starting bot initialization...")
    try:
        await init_db()
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")

        asyncio.create_task(reminder_task())
        await dp.start_polling(bot, skip_updates=True, allowed_updates=["message"])
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        raise
    finally:
        await close_db()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
