from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analyze import router as analyze_router
from routes.journey import router as journey_router


app = FastAPI(
    title="CrowdAgent",
    version="1.0.0",
    description="AI-powered Synthetic User Testing Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    
    ],
    allow_credentials=True,         
    allow_methods=["*"],           
    allow_headers=["*"],           
)


@app.get("/")
async def home():
    return {
        "message": "Welcome to CrowdAgent API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "message": "CrowdAgent API is healthy"
    }


app.include_router(analyze_router)
app.include_router(journey_router)
