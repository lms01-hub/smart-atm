from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.database import engine
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.friends import router as friends_router
from app.routers.chats import router as chats_router
from app.routers.analysis import router as analysis_router
from app.routers.atm import router as atm_router


app = FastAPI(
    title="AnsimTalk Backend API",
    description="AnsimTalk Voice Phishing Prevention Backend",
    version="1.0.0",
)


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(friends_router)
app.include_router(chats_router)
app.include_router(analysis_router)
app.include_router(atm_router)


@app.get("/")
def root():
    return {
        "success": True,
        "data": {
            "message": "AnsimTalk Backend API"
        }
    }


@app.get("/health")
def health_check():
    return {
        "success": True,
        "data": {
            "status": "ok"
        }
    }


@app.get("/health/db")
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "success": True,
            "data": {
                "database": "connected"
            }
        }

    except Exception as e:
        print("DB ERROR:", e)

        return {
            "success": False,
            "error": {
                "code": "DATABASE_CONNECTION_FAILED",
                "message": "Failed to connect to database."
            }
        }



