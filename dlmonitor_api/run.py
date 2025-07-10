#!/usr/bin/env python3
"""
Development server runner for DLMonitor API.
Use this script to run the FastAPI application locally.
"""

import uvicorn
from app.core.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Enable auto-reload for development
        log_level=settings.log_level.lower(),
        access_log=True,
    ) 