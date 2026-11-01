from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analyze import router as analyze_router


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


# ── CORS Middleware ──────────────────────────────────────────
# Allow the React frontend to call the backend API.
# Without this, the browser blocks all cross-origin requests.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React dev server
    ],
    allow_credentials=True,         # Allow cookies/auth headers
    allow_methods=["*"],            # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],            # Allow any request headers
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