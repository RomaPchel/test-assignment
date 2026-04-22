from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Insurance Claim Pipeline",
    description="Automated insurance claim processing with validation gates",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
async def root():
    return {"service": "Insurance Claim Pipeline", "status": "healthy", "version": "1.0.0"}
