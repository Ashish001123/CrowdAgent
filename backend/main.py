from fastapi import FastAPI

from routes.analyze import router as analyze_router

app = FastAPI(
    title="CrowdAgent",
    version="1.0.0",
    description="CrowdAgent API"
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