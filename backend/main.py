from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from models import Base, User
from sqlalchemy.orm import sessionmaker
from auth import hash_password
import os

from routers.auth_router import router as auth_router
from routers.firewalls import router as fw_router
from routers.backups import router as backup_router
from routers.security_rating import router as sr_router
from routers.assets import router as asset_router

# Ensure data/backups dirs exist
os.makedirs("/data/backups", exist_ok=True)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create default admin user if no users exist
Session = sessionmaker(bind=engine)
with Session() as db:
    if db.query(User).count() == 0:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
        )
        db.add(admin)
        db.commit()
        print("[INIT] Default user created: admin / admin123 — TROQUE A SENHA!")

app = FastAPI(
    title="FortiCentralizer API",
    description="Centralized FortiGate management platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(fw_router)
app.include_router(backup_router)
app.include_router(sr_router)
app.include_router(asset_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "FortiCentralizer"}
