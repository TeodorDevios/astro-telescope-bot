from datetime import datetime
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder

tf = TimezoneFinder()

def get_tz_offset_by_coords(lat: float, lon: float) -> int:
    """Определяет смещение часового пояса в часах по координатам"""
    timezone_name = tf.timezone_at(lng=lon, lat=lat)
    
    if not timezone_name:
        return 3 
    tz = ZoneInfo(timezone_name)
    offset_seconds = datetime.now(tz).utcoffset().total_seconds()
    
    return int(offset_seconds // 3600)
