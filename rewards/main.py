import asyncio
import os
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tortoise import Tortoise

sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 2)))

from rewards.settings import config
from rewards.tasks import (
    check_pending_airdrops,
    check_waiting_airdrops,
    ping_nodes,
    send_rewards,
)
from rewards.db import init_db

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init_db())
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            ping_nodes, "interval", minutes=config.ping_nodes_interval_munutes
        )
        scheduler.add_job(check_waiting_airdrops, "interval", minutes=1)
        scheduler.add_job(check_pending_airdrops, "interval", seconds=5)
        scheduler.add_job(
            send_rewards,
            "cron",
            hour=config.rewards_hour,
            misfire_grace_time=15 * 60,
            minute=10,
        )
        scheduler.start()
        loop.run_forever()
    finally:
        loop.run_until_complete(Tortoise.close_connections())
