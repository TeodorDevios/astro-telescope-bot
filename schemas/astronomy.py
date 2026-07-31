import re
from typing import Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict, TypeAdapter
from skyfield.api import Star
from loguru import logger

class MessierObject(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    M: str
    T: str
    V: float
    S: str
    RA: str
    Dec: str
    Con: str
    NGC: Optional[str] = None
    N: Optional[str] = None
    skyfield_star: Optional[Star] = None

    @model_validator(mode='after')
    def parse_coordinates(self) -> 'MessierObject':
        try:
            ra_match = re.match(r'(\d+)\s*h\s*([\d.]+)\s*m', self.RA)
            if not ra_match:
                raise ValueError(f"Не удалось распарсить строку RA: {self.RA}")
                
            ra_hours = float(ra_match.group(1)) + float(ra_match.group(2)) / 60.0
            dec_str_clean = self.Dec.replace('′', "'").replace('°', ' ')
            dec_match = re.match(r'([+-]?\d+)\s+(\d+)', dec_str_clean)
            if not dec_match:
                raise ValueError(f"Не удалось распарсить строку Dec: {self.Dec}")
                
            sign = -1.0 if '-' in self.Dec else 1.0
            dec_deg = abs(float(dec_match.group(1)))
            dec_min = float(dec_match.group(2))
            
            dec_degrees = (dec_deg + (dec_min / 60.0)) * sign
            self.skyfield_star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
            
        except Exception as e:
            logger.error(f"Ошибка парсинга координат для {self.M}: {e}")
            
        return self