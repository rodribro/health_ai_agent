from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import ai, health, patients
from .config import settings
from huggingface_hub import InferenceClient
from typing import Optional
from contextlib import asynccontextmanager
from .services import ai_service



@asynccontextmanager
async def lifespan(app: FastAPI):
   
    print("Starting Health AI Agent...")
    success = await ai_service.initialize()

    if success:
        print("AI service initialized successfully")
    else:
        print("Warning: AI service initialization failed")
    
    yield
    
    print("Shutting down Health AI Agent...")

app = FastAPI(
    title="Health AI Agent",
    description="MIMIC-III discharge summary analysis using Llama3-Med42",
    version="0.1.0",
    lifespan=lifespan
)

# CORS setup for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Need to change this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(patients.router, prefix="/patients", tags=["patients"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])

@app.get("/")
async def root():
    return {"message": "Health AI Agent API", "version": "0.1.0"}