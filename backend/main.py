
from fastapi import FastAPI

app = FastAPI(
    title="CampusMind AI",
    description="AI-powered energy optimization system for university campuses",
    version="0.1.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to CampusMind AI!",
        "version": "0.1.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }
