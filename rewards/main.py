import asyncio
import os
import sys
from tortoise import Tortoise
from apscheduler.schedulers.asyncio import AsyncIOScheduler

sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 2)))

from rewards.settings import POSTGRES_URL, MODELS_MODULE, config
from rewards.tasks import ping_nodes, send_rewards, check_pending_airdrops, check_waiting_airdrops



async def init_db():
    await Tortoise.init(db_url=POSTGRES_URL, modules={"models": [MODELS_MODULE]})
    await Tortoise.generate_schemas()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init_db())
        scheduler = AsyncIOScheduler()
        scheduler.add_job(ping_nodes, "interval", minutes=1)
        scheduler.add_job(check_waiting_airdrops, 'interval', minutes=1)
        scheduler.add_job(check_pending_airdrops, 'interval', seconds=5)
        scheduler.add_job(send_rewards, 'cron', hour=config.rewards_hour)
        scheduler.start()
        loop.run_forever()
    finally:
        loop.run_until_complete(Tortoise.close_connections())
   