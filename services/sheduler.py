from datetime import datetime
from aiogram import Bot
from sqlalchemy import select
from loguru import logger

from db.core import get_db_session
from db.models import User
from db.requests import get_user_profile
from services.astronomy import get_object_visibility
from config.config import PLANET_MAPPING, MESSIER_CATALOG 


async def send_daily_forecast(bot: Bot):
    """
    Генератор ежедневной утренней рассылки.
    Сканирует базу, рассчитывает видимость и шлет персональные отчеты юзерам.
    """
    logger.info("Запуск процесса ежедневной астро-рассылки...")
    
    async with get_db_session() as session:
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        
    for raw_user in all_users:
        async with get_db_session() as session:
            user = await get_user_profile(session, raw_user.telegram_id)
            
        if not user or not user.latitude or not user.telescope:
            continue
            
        visible_planets = []
        visible_messier = []
        
        # 1. Цикл проверки всех планет
        for planet_name in PLANET_MAPPING.keys():
            res = await get_object_visibility(
                lat=user.latitude,
                lon=user.longitude,
                object_name=planet_name,
                target_date=datetime.now(),
                user_tz_offset=user.tz_offset
            )
            if res and res['visibility'] and res['rise_times']:
                rises = ", ".join(res['rise_times'])
                visible_planets.append(f"🪐 {res['object']} — восход в {rises} (яркость: {res['brightness']}m)")
        for m_id, m_obj in list(MESSIER_CATALOG.items())[:10]:
            res = await get_object_visibility(
                lat=user.latitude,
                lon=user.longitude,
                object_name=m_id,
                target_date=datetime.now(),
                user_tz_offset=user.tz_offset
            )
            if res and res['visibility']:
                name_str = f" ({m_obj.N})" if m_obj.N else ""
                visible_messier.append(
                    f"✨ {m_id}{name_str} в созвездии **{m_obj.Con}** (яркость: {res['brightness']}m)"
                )

        if not visible_planets and not visible_messier:
            continue  
            
        text = "🌌 **Астрономический прогноз видимости на грядущую ночь:**\n\n"
        
        text += "📈 **Доступные планеты:**\n"
        text += ("\n".join(visible_planets) if visible_planets else "Сегодня планет не видно.") + "\n\n"
        
        text += "🔭 **Объекты Мессье и созвездия:**\n"
        text += "\n".join(visible_messier) if visible_messier else "Сегодня объекты глубокого космоса недоступны."
        
        try:
            await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode="Markdown")
            logger.info(f"Рассылка успешно улетела пользователю {user.telegram_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить рассылку пользователю {user.telegram_id}: {e}")
