from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import optimizer, production_lines, shifts, skills, workers

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Production Line Scheduler",
    description="Optimize worker rotation across production line stations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(skills.router)
app.include_router(workers.router)
app.include_router(shifts.router)
app.include_router(production_lines.router)
app.include_router(optimizer.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Serve frontend static files if the built frontend directory exists.
# This allows running the app standalone without Nginx (e.g. on Windows).
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")
