"""LabelGuard AI - FastAPI application entry point."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI

# Reads backend/.env when present so os.getenv() below sees local settings.
load_dotenv()

app = FastAPI(
    title="LabelGuard AI",
    description="AI-assisted Legal Metrology compliance inspection platform.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Report that the service is running."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
