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

## How the Optimizer Works

The optimizer lives in `backend/app/services/optimizer.py` and uses the
**Google OR-Tools CP-SAT** constraint-programming solver (30-second time limit).

### Inputs

| Input | Source |
|---|---|
| Workers (id, name, skill list) | Shift assignments for the selected shift |
| Stations (workers needed, max minutes per worker, required skills) | Active stations on the selected production line |
| Slot duration (minutes) | User-configurable (default 30 min) |
| Shift duration | Derived from the shift's start/end hours |

The shift is divided into **N time slots** (`shift_duration / slot_duration`).

### Decision Variables

- `x[w][s][t]` (binary) — is worker **w** assigned to station **s** during slot **t**?
- `y[w][s]` (binary indicator) — was worker **w** ever assigned to station **s**?

### Eligibility

Before solving, an eligibility matrix is computed: a worker can only be assigned
to a station if they possess **all** of that station's required skills. Stations
with no required skills accept any worker.

### Constraints

1. **Staffing**: each station gets exactly `workers_needed` workers in every slot.
2. **No double-booking**: each worker is at most one station per slot.
3. **Max time limit**: a worker cannot exceed `max_minutes_per_worker` total at
   any single station (enforced as `max_minutes / slot_duration` slots).

### Objective

Maximize **rotation diversity** — the number of distinct (worker, station) pairs
that have at least one assignment. This spreads workers across different stations
rather than parking them at the same station for the entire shift.

### Diagnostics

When the solver returns **infeasible**, a diagnostic pass checks for common
causes and returns human-readable messages:

- Not enough total workers vs. total simultaneous demand across all stations.
- Not enough **skilled** workers for a specific station.
- Not enough eligible workers to sustain **rotation** given `max_minutes_per_worker`.

### Output

The result is a list of time slots, each containing per-station assignments with
worker IDs and names. The frontend displays this as:

- A **schedule table** (stations as columns, time slots as rows).
- A **Gantt chart** (workers on the Y-axis, time on the X-axis, bars color-coded
  by station).

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
