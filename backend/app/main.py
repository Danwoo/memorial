from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.v1.router import api_router

app = FastAPI(
    title="Memoir AI",
    description="지능형 인지 장부 - Backend API",
    version="0.1.0"
)

# CORS 설정 (Frontend 연동 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow Extension & Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# API Router 연결
app.include_router(api_router)

