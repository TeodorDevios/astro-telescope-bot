from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from .models import User, Telescope, Eyepiece


async def get_user_profile(session: AsyncSession, tg_id: int) -> User | None:
    """Получает профиль пользователя"""
    try:
        query = (
            select(User)
            .where(User.telegram_id == tg_id)
            .options(
                selectinload(User.telescope).selectinload(Telescope.eyepieces)
            )
        )
        result = await session.execute(query)
        logger.info(f'Успешно получены данные для пользователя {tg_id}')
        return result.scalar_one_or_none()
    except Exception as ex:
        logger.error(f'Ошибка при обработке пользователя {tg_id}: {ex}')


async def upsert_user_coords(session: AsyncSession, tg_id: int, lat: float, lon: float, tz: int) -> None:
    """Создает пользователя или обновляет его гео-данные и часовой пояс"""
    user = await session.get(User, tg_id)
    
    if user:
        user.latitude = lat
        user.longitude = lon
        user.tz_offset = tz
    else:
        new_user = User(telegram_id=tg_id, latitude=lat, longitude=lon, tz_offset=tz)
        session.add(new_user)


async def save_telescope(session: AsyncSession, tg_id: int, diameter: float, focal_length: float) -> None:
    """Создает или обновляет оптическую трубу телескопа для пользователя"""
    query = select(User).where(User.telegram_id == tg_id).options(selectinload(User.telescope))
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_id=tg_id)
        session.add(user)
        
    if user.telescope:
        user.telescope.diameter = diameter
        user.telescope.focal_length = focal_length
    else:
        new_telescope = Telescope(diameter=diameter, focal_length=focal_length)
        user.telescope = new_telescope


async def add_eyepiece(session: AsyncSession, tg_id: int, eyepiece_f: float, name: str) -> None:
    """
    Добавляет новый окуляр в чемоданчик. 
    Если это первый окуляр пользователя — автоматически делает его активным.
    """
    query = select(User).where(User.telegram_id == tg_id).options(
        selectinload(User.telescope).selectinload(Telescope.eyepieces)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not user.telescope:
        raise ValueError("Сначала необходимо настроить параметры телескопа!")
        
    is_first = len(user.telescope.eyepieces) == 0
    
    new_eyepiece = Eyepiece(
        eyepiece_focal_length=eyepiece_f,
        name=name,
        is_active=is_first
    )
    user.telescope.eyepieces.append(new_eyepiece)


async def set_active_eyepiece(session: AsyncSession, tg_id: int, eyepiece_id: int) -> None:
    """Переключает активный окуляр: выбранному ставит True, остальным окулярам юзера — False"""
    query = select(User).where(User.telegram_id == tg_id).options(
        selectinload(User.telescope).selectinload(Telescope.eyepieces)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user and user.telescope:
        for ep in user.telescope.eyepieces:
            ep.is_active = (ep.id == eyepiece_id)

