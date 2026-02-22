from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_origins=["http://localhost:5173"],
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
