from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    ProductionLine,
    Shift,
    ShiftAssignment,
    Station,
)
from app.schemas import OptimizationRequest, OptimizationResult
from app.services.optimizer import optimize_schedule

router = APIRouter(prefix="/api/optimize", tags=["optimizer"])


@router.post("", response_model=OptimizationResult)
def run_optimization(
    request: OptimizationRequest, db: Session = Depends(get_db)
):
    # Validate production line
    line = (
        db.query(ProductionLine)
        .filter(ProductionLine.id == request.production_line_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")

    # Validate shift
    shift = db.query(Shift).filter(Shift.id == request.shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Get active stations for this line
    stations_db = (
        db.query(Station)
        .filter(
            Station.production_line_id == request.production_line_id,
            Station.active.is_(True),
        )
        .order_by(Station.position)
        .all()
    )
    if not stations_db:
        raise HTTPException(
            status_code=400,
            detail="No active stations in this production line",
        )

    # Get workers assigned to this shift
    assignments = (
        db.query(ShiftAssignment)
        .filter(ShiftAssignment.shift_id == request.shift_id)
        .all()
    )
    if not assignments:
        raise HTTPException(
            status_code=400,
            detail="No workers assigned to this shift",
        )

    # Build data structures for optimizer
    workers = []
    for a in assignments:
        w = a.worker
        if not w.active:
            continue
        workers.append(
            {
                "id": w.id,
                "name": w.name,
                "skill_ids": [s.id for s in w.skills],
            }
        )

    stations = []
    for s in stations_db:
        stations.append(
            {
                "id": s.id,
                "name": s.name,
                "workers_needed": s.workers_needed,
                "max_minutes_per_worker": s.max_minutes_per_worker,
                "required_skill_ids": [sk.id for sk in s.required_skills],
            }
        )

    # Calculate shift duration
    shift_duration_minutes = int((shift.end_hour - shift.start_hour) * 60)
    if shift_duration_minutes <= 0:
        raise HTTPException(
            status_code=400, detail="Invalid shift duration"
        )

    return optimize_schedule(request, workers, stations, shift_duration_minutes)
