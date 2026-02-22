# Production Line Scheduler

Optimize worker rotation across production line stations. Ensures workers rotate
within configurable time limits while respecting skill requirements.

## Architecture

- **Backend**: Python / FastAPI / SQLAlchemy / SQLite
- **Frontend**: React / TypeScript / Vite / TanStack Query
- **Optimizer**: Google OR-Tools (CP-SAT constraint solver)
- **i18n**: i18next (English + Spanish, extensible)

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. API calls are proxied to the backend.

## Features

- **Skills**: Define skills that workers can have and stations can require
- **Workers**: Create workers with name and skill assignments
- **Shifts**: Define shifts (start/end hours) and assign workers to shifts
- **Production Lines**: Create lines with ordered stations, each configurable with:
  - Number of workers needed
  - Max minutes a worker can stay at the station
  - Cycle time
  - Required skills
- **Optimizer**: Select a production line and shift, choose rotation slot duration,
  and generate an optimal schedule matrix that rotates workers while respecting
  all constraints

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET/POST /api/skills` | Manage skills |
| `GET/POST /api/workers` | Manage workers |
| `GET/POST /api/shifts` | Manage shifts |
| `POST /api/shifts/assignments` | Assign workers to shifts |
| `GET/POST /api/production-lines` | Manage production lines |
| `POST /api/production-lines/{id}/stations` | Manage stations |
| `POST /api/optimize` | Run schedule optimization |
