from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from src.settings import MODELS_MODULE, POSTGRES_URL


async def init_db(app: FastAPI = None) -> None:
    if app:
        register_tortoise(
            app,
            db_url=POSTGRES_URL,
            modules={"models": MODELS_MODULE},
            generate_schemas=False,
            add_exception_handlers=True,
        )
        return
    else:
        await Tortoise.init(db_url=POSTGRES_URL, modules={"models": MODELS_MODULE})
        await Tortoise.generate_schemas()
