from datetime import datetime, timezone, timedelta
import numpy as np  # Импортируем для безопасной работы с типами Skyfield
from skyfield.api import wgs84, load, Star
from skyfield.almanac import risings_and_settings, find_discrete
from skyfield.magnitudelib import planetary_magnitude
from loguru import logger

from config.config import PLANET_MAPPING, MESSIER_CATALOG

ts = load.timescale()
planets = load('de421.bsp')

async def get_object_visibility(
    lat: float, 
    lon: float, 
    object_name: str, 
    target_date: datetime,
    user_tz_offset: int = 3
) -> dict | None:
    """
    Универсальная асинхронная функция расчета видимости и яркости объектов.
    Автоматически адаптирует суточное окно под локальный часовой пояс пользователя.
    """
    tz_user = timezone(timedelta(hours=user_tz_offset))
    name_upper = object_name.upper().strip()
    name_lower = object_name.lower().strip()
    
    target_object = None
    current_brightness = 0.0

    earth = planets['earth']
    
    geo_location = wgs84.latlon(lat, lon)
    observer = earth + geo_location
    naive_date = target_date.replace(tzinfo=None)
    
    if name_lower in PLANET_MAPPING:
        try:
            target_object = planets[PLANET_MAPPING[name_lower]]
            local_midnight = datetime(
                year=naive_date.year, month=naive_date.month, day=naive_date.day,
                hour=0, minute=0, second=0, tzinfo=tz_user
            )
            t_midnight = ts.from_datetime(local_midnight.astimezone(timezone.utc))
            
            astrometric = observer.at(t_midnight).observe(target_object)
            mag_array = planetary_magnitude(astrometric)
            current_brightness = float(mag_array) if not isinstance(mag_array, float) else mag_array
            
        except (ValueError, KeyError) as e:
            logger.error(f'Планета {object_name} не найдена в файле эфемерид: {e}')
            return None
    else:
        messier_obj = MESSIER_CATALOG.get(name_upper)
        if not messier_obj:
            logger.error(f'Объект {object_name} не найден ни в планетах, ни в каталоге Мессье')
            return None
            
        target_object = messier_obj.skyfield_star
        current_brightness = messier_obj.V
    local_noon = datetime(
        year=naive_date.year, month=naive_date.month, day=naive_date.day,
        hour=12, minute=0, second=0, tzinfo=tz_user
    )
    start_dt = local_noon.astimezone(timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    t0 = ts.from_datetime(start_dt)
    t1 = ts.from_datetime(end_dt)
    
    f = risings_and_settings(planets, target_object, geo_location)
    t_events, y_events = find_discrete(t0, t1, f)
    
    rise_times = [t for t, y in zip(t_events, y_events) if y == 1]
    setting_times = [t for t, y in zip(t_events, y_events) if y == 0]
    
    # Форматирование времени в локальную таймзону пользователя
    rise_strings = [t.astimezone(tz_user).strftime('%H:%M') for t in rise_times]
    set_strings = [t.astimezone(tz_user).strftime('%H:%M') for t in setting_times]
    
    if rise_strings or set_strings:
        visibility = True
    else:
        local_midnight = datetime(
            year=naive_date.year, month=naive_date.month, day=naive_date.day,
            hour=0, minute=0, second=0, tzinfo=tz_user
        )
        t_midnight = ts.from_datetime(local_midnight.astimezone(timezone.utc))
        
        alt, _, _ = observer.at(t_midnight).observe(target_object).apparent().altaz()
        alt_degrees = float(alt.degrees) if not isinstance(alt.degrees, float) else alt.degrees
        visibility = alt_degrees > 0
        
    logger.info(f'Видимость и яркость объекта {object_name} успешно получены')
    
    return {
        'object': name_upper,
        'visibility': visibility, 
        'rise_times': rise_strings, 
        'setting_times': set_strings,
        'brightness': round(float(current_brightness), 2)  
    }
