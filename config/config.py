import json

from pydantic import SecretStr, HttpUrl, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict
from aiogram import Bot, Dispatcher

from schemas.astronomy import MessierObject


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    telegram_api_token: SecretStr


SETTINGS = Settings()

bot = Bot(token=SETTINGS.telegram_api_token.get_secret_value())
dp = Dispatcher()


PLANET_MAPPING = {
    'mercury': 'mercury', 'venus': 'venus', 'earth': 'earth', 'mars': 'mars',
    'jupiter': 'jupiter barycenter', 'saturn': 'saturn barycenter',
    'uranus': 'uranus barycenter', 'neptune': 'neptune barycenter',
    'pluto': 'pluto barycenter', 'moon': 'moon', 'sun': 'sun'
}


def _load_all_messier_objects(file_path: str) -> dict[str, MessierObject]:
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    adapter = TypeAdapter(list[MessierObject])
    messier_list = adapter.validate_python(raw_data)
    messier_dict = {obj.M: obj for obj in messier_list}
    return messier_dict


MESSIER_CATALOG = _load_all_messier_objects('data/messier.json')