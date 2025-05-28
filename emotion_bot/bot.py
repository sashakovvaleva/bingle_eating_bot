# emotion_bot/bot.py
# Last updated: 2025-05-27 - Added detailed emotion descriptions

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
            "Привет! 👋\n\n"
            "Я — твой личный бот-дневник питания и эмоций. Помогаю отслеживать, что и как ты ешь, "
            "а также как это влияет на твоё настроение, эмоциональное состояние и здоровье в целом.\n\n"
            "📌 Вот как мы будем работать вместе:\n"
            "1️⃣ Ты будешь записывать приёмы пищи (можно быстро и в любое время).\n"
            "2️⃣ Я задам несколько коротких вопросов: каков был голод до еды, насколько ты насытился(лась), "
            "где ты ел(а), с кем, как себя чувствовал(а) и т.д.\n"
            "3️⃣ Это поможет тебе замечать связи между эмоциями, питанием и самочувствием, "
            "а также отслеживать переедания или пищевые срывы.\n\n"
            "✨ Чтобы начать, скажи, пожалуйста, как тебя зовут?\n\n"
            "📥 Введи своё имя в ответ на это сообщение 👇"
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
        keyboard=[
            [KeyboardButton(text="🏠 Дома"), KeyboardButton(text="💼 Работа/Учеба")],
            [KeyboardButton(text="🍽️ Кафе/Ресторан"), KeyboardButton(text="🚶 На ходу")],
            [KeyboardButton(text="🚗 В машине"), KeyboardButton(text="🏢 В гостях")],
            [KeyboardButton(text="🌳 На природе"), KeyboardButton(text="📱 Другое")]
        ],
        resize_keyboard=True
    )
    await message.answer("Где ты ел(а)? Выбери наиболее подходящий вариант:", reply_markup=kb)
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
        # Проверяем, был ли уже введен день цикла сегодня
        cycle_day = await get_last_cycle_day(message.from_user.id)
        if cycle_day is not None:
            # Если день цикла уже был введен сегодня, используем его
            await state.update_data(cycle_day=cycle_day)
            await ask_binge(message, state)
        else:
            # Если день цикла еще не был введен, спрашиваем
            await message.answer(
                "Какой сегодня день цикла?\n\n"
                "📝 Введи число от 1 до 40\n"
                "(В зависимости от длины твоего цикла эта цифра может варьироваться)\n\n"
                "• 1-5 день: менструация\n"
                "• 6-14 день: фолликулярная фаза\n"
                "• 15-28 день: лютеиновая фаза\n"
                "• 29-40 день: возможна задержка",
                reply_markup=types.ReplyKeyboardRemove()
            )
            await state.set_state(DiaryForm.cycle_day)
    else:
        await ask_binge(message, state)

@dp.message(DiaryForm.cycle_day)
async def cycle_day(message: types.Message, state: FSMContext):
    cycle_day = int(message.text)
    await state.update_data(cycle_day=cycle_day)
    # Сохраняем день цикла в отдельную таблицу
    await save_cycle_day(message.from_user.id, cycle_day)
    await ask_binge(message, state)

async def ask_binge(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Нет, обычный приём пищи"), KeyboardButton(text="⚠️ Лёгкое переедание")],
            [KeyboardButton(text="❗ Сильное переедание"), KeyboardButton(text="🔥 Срыв/компульсивное переедание")],
            [KeyboardButton(text="🤔 Не уверен(а)"), KeyboardButton(text="💭 Хочу отметить детали")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Как ты оцениваешь этот приём пищи?\n\n"
        "• Обычный приём пищи — ты съел(а) столько, сколько планировал(а)\n"
        "• Лёгкое переедание — съел(а) больше обычного, но без сильного дискомфорта\n"
        "• Сильное переедание — съел(а) значительно больше, есть дискомфорт\n"
        "• Срыв — потеря контроля над количеством еды\n"
        "• Не уверен(а) — сложно оценить\n"
        "• Хочу отметить детали — есть что добавить",
        reply_markup=kb
    )
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

async def send_daily_reminder():
    """Send daily reminder to all users"""
    logger.info("Sending daily reminders...")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get all unique user IDs
            users = await conn.fetch("SELECT DISTINCT id FROM users")
            logger.info(f"Found {len(users)} users to send reminders")
            for user in users:
                try:
                    await bot.send_message(
                        user['id'],
                        "Небольшое напоминание 🌿\n\n"
                        "Если вдруг почувствуешь, что хочется записать, как ты себя сегодня ощущаешь — это может помочь общему процессу. Всё по желанию, никакой спешки и обязательств.\n\n"
                        "Твоё участие для нас действительно важно. Каждый из нас — часть чего-то большего. Спасибо, что ты уделяешь время и делишься чувствами.",
                        reply_markup=ReplyKeyboardMarkup(
                            keyboard=[[KeyboardButton(text="📝 Записать приём пищи")]],
                            resize_keyboard=True
                        )
                    )
                    logger.info(f"Reminder sent to user {user['id']}")
                except Exception as e:
                    logger.error(f"Failed to send reminder to user {user['id']}: {e}")
    except Exception as e:
        logger.error(f"Error in daily reminder: {e}")

async def main():
    try:
        logger.info("Starting bot...")
        await init_db()
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in bot: {e}")
    finally:
        await close_db()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
