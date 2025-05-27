# emotion_bot/bot.py
# Last updated: 2025-05-27 - Added detailed emotion descriptions

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from database import init_db, insert_entry, get_user, save_user, close_db
from dotenv import load_dotenv
import os
import logging
import sys

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
        await message.answer(f"Снова здравствуй, {name}!\n\nКоманда: /meal — начать запись приема пищи")
    else:
        await state.set_state(DiaryForm.name)
        await message.answer(
            "Привет! 👋\n\n"
            "Я — твой личный бот-дневник питания и эмоций. Помогаю отслеживать, что и как ты ешь, "
            "а также как это влияет на твоё настроение, эмоциональное состояние и здоровье в целом.\n\n"
            "📌 Вот как мы будем работать вместе:\n"
            "1️⃣ Ты будешь записывать приёмы пищи (можно быстро и в любое время).\n"
            "2️⃣ Я задам несколько коротких вопросов: каков был голод до еды, насколько ты насытился(лась), "
            "где ты ел(а), с кем, как себя чувствовал(а) и т.д.\n"
            "3️⃣ Это поможет тебе замечать связи между эмоциями, питанием и самочувствием, "
            "а также отслеживать переедания или пищевые срывы.\n\n"
            "🔄 Когда ты захочешь сделать запись — просто введи команду /meal (можно в любое время).\n"
            "✨ Чтобы начать, скажи, пожалуйста, как тебя зовут?\n\n"
            "📥 Введи своё имя в ответ на это сообщение 👇"
        )

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
        "😐 Нейтрально / никаких ярких эмоций",
        "😊 Радость / удовлетворение / спокойствие",
        "😢 Грусть / разочарование / одиночество",
        "😠 Злость / раздражение / обида",
        "😰 Тревога / беспокойство / паника",
        "😴 Усталость / опустошение / вялость",
        "😞 Стыд / вина / самокритика",
        "🤯 Стресс / давление / перегрузка",
        "🥱 Скука / апатия / безразличие",
        "😍 Вдохновение / воодушевление / благодарность"
    ]
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=emotion)] for emotion in emotions],
        resize_keyboard=True
    )
    await message.answer("Какую эмоцию ты испытывал(а)? Выбери наиболее подходящее описание своего состояния:", reply_markup=kb)
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
        keyboard=[[KeyboardButton(text="дома"), KeyboardButton(text="работа"), KeyboardButton(text="кафе")]],
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
    await message.answer("Ты ел(а) один/одна или с кем-то?", reply_markup=kb)
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
        await message.answer("Какой сегодня день цикла?")
        await state.set_state(DiaryForm.cycle_day)
    else:
        await ask_binge(message, state)

@dp.message(DiaryForm.cycle_day)
async def cycle_day(message: types.Message, state: FSMContext):
    await state.update_data(cycle_day=int(message.text))
    await ask_binge(message, state)

async def ask_binge(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
            [KeyboardButton(text="Лёгкое"), KeyboardButton(text="Сильное")]
        ],
        resize_keyboard=True
    )
    await message.answer("Было ли переедание/срыв?", reply_markup=kb)
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

async def main():
    logger.info("Starting bot initialization...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)
        bot_info = await bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")
        await dp.start_polling(bot, skip_updates=True, allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error(f"Error during bot startup: {e}")
        if "Conflict" in str(e):
            logger.error("Bot conflict detected. Check Railway dashboard for duplicate instances.")
        raise
    finally:
        logger.info("Shutting down bot...")
        await close_db()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
