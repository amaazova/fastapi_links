import logging
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import redis.asyncio as aioredis
from config import REDIS_URL
from database import init_models
from routers import users, links
from tasks import celery_app

logger = logging.getLogger(__name__)
app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="FastAPI URL Shortener",
        version="1.0.0",
        description="API for URL shortening service",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path, methods in openapi_schema["paths"].items():
        for method, details in methods.items():
            if path == "/users/links" and method.lower() == "get":
                details["security"] = [{"BearerAuth": []}]
            elif path.startswith("/{") and method.lower() in ["put", "delete"]:
                details["security"] = [{"BearerAuth": []}]
            elif path.startswith("/shorten") and method.lower() == "post":
                if path != "/shorten/public":
                    details["security"] = [{"BearerAuth": []}]
            elif path.startswith("/token/refresh"):
                details["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(links.router, tags=["links"])

redis_client = None

@app.on_event("startup")
async def startup():
    await init_models()
    global redis_client
    redis_client = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=False)

@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()
