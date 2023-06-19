from fastapi import FastAPI

from rewards.db import init_db

from rewards.api import router

def get_application() -> FastAPI:
    _app = FastAPI(
        title='Raspberry Rewards Backend',
        docs_url="/api/v1/swagger/",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
    )

    return _app

web = get_application()
web.include_router(router)

@web.on_event("startup")
async def startup_event():
    await init_db(web)

@web.on_event("shutdown")
async def shutdown_event():
    pass
