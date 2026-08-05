
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from config.config import bot
from services.sheduler import send_daily_forecast

forecast = Router()


@forecast.message(Command('forecast'))
async def forecast_message(message: Message):
    await send_daily_forecast(bot)