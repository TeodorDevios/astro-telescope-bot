from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from loguru import logger

from db.core import get_db_session
from db.requests import upsert_user_coords, save_telescope, add_eyepiece, get_user_profile
from services.timezone import get_tz_offset_by_coords

profile = Router()


class ProfileForm(StatesGroup):
    waiting_for_diameter = State()
    waiting_for_focal_length = State()
    waiting_for_eyepiece_f = State()
    waiting_for_eyepiece_name = State()
    waiting_for_location = State()


class EyepieceForm(StatesGroup):
    waiting_for_f = State()
    waiting_for_name = State()



@profile.message(CommandStart())
@profile.message(Command("set_profile"))
async def start_profile_wizard(message: Message, state: FSMContext):
    async with get_db_session() as session:
        user = await get_user_profile(session, message.from_user.id)
    
    greeting = "Привет! Давай настроим твой астро-профиль.\n" if not user else "Обновляем твой профиль.\n"
    await message.answer(f"{greeting}Шаг 1/5: Введи диаметр объектива/зеркала телескопа (D) в мм:")
    await state.set_state(ProfileForm.waiting_for_diameter)


@profile.message(ProfileForm.waiting_for_diameter)
async def process_diameter(message: Message, state: FSMContext):
    try:
        d = float(message.text)
        if d <= 0: raise ValueError
        await state.update_data(diameter=d)
        await message.answer("Шаг 2/5: Введи фокусное расстояние трубы телескопа (F) в мм:")
        await state.set_state(ProfileForm.waiting_for_focal_length)
    except ValueError:
        await message.answer("Пожалуйста, введи корректное положительное число (например, 150):")


@profile.message(ProfileForm.waiting_for_focal_length)
async def process_telescope_f(message: Message, state: FSMContext):
    try:
        f = float(message.text)
        if f <= 0: raise ValueError
        await state.update_data(focal_length=f)
        await message.answer("Шаг 3/5: Введи фокусное расстояние твоего основного окуляра (f) в мм:")
        await state.set_state(ProfileForm.waiting_for_eyepiece_f)
    except ValueError:
        await message.answer("Пожалуйста, введи корректное положительное число (например, 750):")


@profile.message(ProfileForm.waiting_for_eyepiece_f)
async def process_eyepiece_f(message: Message, state: FSMContext):
    try:
        ef = float(message.text)
        if ef <= 0: raise ValueError
        await state.update_data(eyepiece_f=ef)
        await message.answer("Шаг 4/5: Дай имя этому окуляру (например, 'Обзорный 25мм' или 'Плёссл'):")
        await state.set_state(ProfileForm.waiting_for_eyepiece_name)
    except ValueError:
        await message.answer("Пожалуйста, введи корректное положительное число (например, 25):")


@profile.message(ProfileForm.waiting_for_eyepiece_name)
async def process_eyepiece_name(message: Message, state: FSMContext):
    await state.update_data(eyepiece_name=message.text.strip())
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Отправить геопозицию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Шаг 5/5: Нажми на кнопку ниже, чтобы отправить свою геопозицию:", reply_markup=kb)
    await state.set_state(ProfileForm.waiting_for_location)


@profile.message(ProfileForm.waiting_for_location, F.location)
async def process_location(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    
    tz_offset = get_tz_offset_by_coords(lat, lon)
    
    data = await state.get_data()
    
    async with get_db_session() as session:
        await upsert_user_coords(session, tg_id, lat, lon, tz_offset)
        await save_telescope(session, tg_id, data['diameter'], data['focal_length'])
        await add_eyepiece(session, tg_id, data['eyepiece_f'], data['eyepiece_name'])
    
    await state.clear()
    await message.answer(
        f"🎉 Профиль успешно настроен!\n"
        f"Координаты: {lat:.4f}, {lon:.4f} (UTC+{tz_offset})\n"
        f"Телескоп: D={data['diameter']}мм, F={data['focal_length']}мм\n"
        f"Окуляр '{data['eyepiece_name']}' установлен как активный.",
        reply_markup=ReplyKeyboardRemove()
    )



@profile.message(Command("add_eyepiece"))
async def start_eyepiece_wizard(message: Message, state: FSMContext):
    async with get_db_session() as session:
        user = await get_user_profile(session, message.from_user.id)
        
    if not user or not user.telescope:
        await message.answer("Сначала настрой профиль телескопа с помощью команды /set_profile")
        return

    await message.answer("Введи фокусное расстояние нового окуляра (f) в мм:")
    await state.set_state(EyepieceForm.waiting_for_f)


@profile.message(EyepieceForm.waiting_for_f)
async def process_new_ep_f(message: Message, state: FSMContext):
    try:
        ef = float(message.text)
        if ef <= 0: raise ValueError
        await state.update_data(eyepiece_f=ef)
        await message.answer("Введи название для этого окуляра (например, 'Планетарный 6мм'):")
        await state.set_state(EyepieceForm.waiting_for_name)
    except ValueError:
        await message.answer("Пожалуйста, введи корректное положительное число:")


@profile.message(EyepieceForm.waiting_for_name)
async def process_new_ep_name(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    name = message.text.strip()
    data = await state.get_data()
    
    async with get_db_session() as session:
        await add_eyepiece(session, tg_id, data['eyepiece_f'], name)
        
    await state.clear()
    await message.answer(f"✅ Окуляр '{name}' ({data['eyepiece_f']}мм) успешно добавлен в твой чемоданчик!")
