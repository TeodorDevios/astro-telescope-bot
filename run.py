import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.config import dp, bot
from bot.handlers import routers
from db.core import init_db
from services.sheduler import send_daily_forecast 

async def main():
    for _ in routers:
        dp.include_router(_)
    await init_db()
    
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    scheduler.add_job(
        send_daily_forecast, 
        trigger="cron", 
        hour=8, 
        minute=0, 
        kwargs={"bot": bot}
    )
    
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
