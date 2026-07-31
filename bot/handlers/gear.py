import math

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru  import logger

from db.core import get_db_session
from db.requests import get_user_profile, set_active_eyepiece


gear = Router()

def build_gear_keyboard(user) -> InlineKeyboardMarkup:
    """Вспомогательная функция сборки кнопок со списком окуляров"""
    keyboard_buttons = []
    
    eyepieces = sorted(user.telescope.eyepieces, key=lambda e: e.eyepiece_focal_length, reverse=True)
    
    for ep in eyepieces:
        status_emoji = "🟢 " if ep.is_active else ""
        button_text = f"{status_emoji}{ep.name} ({ep.eyepiece_focal_length}мм)"
        callback_data = f"set_ep_{ep.id}"
        keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


@gear.message(Command("my_gear"))
async def show_my_gear(message: Message):
    async with get_db_session() as session:
        user = await get_user_profile(session, message.from_user.id)
        
    if not user or not user.telescope:
        await message.answer("Твой профиль оборудования не настроен. Напиши /set_profile")
        return
    d = user.telescope.diameter
    f_scope = user.telescope.focal_length
    max_g = d * 2
    min_g = round(d / 6.5, 1)
    m_lim = round(2.7 + 5 * (math.log10(d) if d > 0 else 0), 2)
    
    text = (
        f"🔭 **Твой оптический сетап:**\n"
        f"Труба: Диаметр D = {d}мм, Фокус F = {f_scope}мм\n"
        f"Проницающая способность: до {m_lim}m звездной величины\n"
        f"Пределы увеличений трубы: от {min_g}х до {max_g}х\n\n"
        f"💼 **Твой чемоданчик окуляров:**\n"
        f"Выбери окуляр ниже, чтобы надеть его на телескоп прямо сейчас:"
    )
    
    kb = build_gear_keyboard(user)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@gear.callback_query(F.data.startswith("set_ep_"))
async def handle_change_eyepiece(callback: CallbackQuery):
    tg_id = callback.from_user.id
    eyepiece_id = int(callback.data.split("_")[2])
    
    async with get_db_session() as session:
        # Переключаем статус в БД
        await set_active_eyepiece(session, tg_id, eyepiece_id)
        user = await get_user_profile(session, tg_id)
        
    kb = build_gear_keyboard(user)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Окуляр успешно заменен!")
