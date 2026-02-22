from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Shift, ShiftAssignment, Worker
from app.schemas import (
    ShiftAssignmentCreate,
    ShiftAssignmentOut,
    ShiftCreate,
    ShiftOut,
)

router = APIRouter(prefix="/api/shifts", tags=["shifts"])


# --- Shifts ---
@router.get("", response_model=list[ShiftOut])
def list_shifts(db: Session = Depends(get_db)):
    return db.query(Shift).all()


@router.post("", response_model=ShiftOut, status_code=201)
def create_shift(data: ShiftCreate, db: Session = Depends(get_db)):
    shift = Shift(
        name=data.name,
        start_hour=data.start_hour,
        end_hour=data.end_hour,
        active=data.active,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/{shift_id}", response_model=ShiftOut)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


@router.put("/{shift_id}", response_model=ShiftOut)
def update_shift(shift_id: int, data: ShiftCreate, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    shift.name = data.name
    shift.start_hour = data.start_hour
    shift.end_hour = data.end_hour
    shift.active = data.active
    db.commit()
    db.refresh(shift)
    return shift


@router.delete("/{shift_id}", status_code=204)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    db.delete(shift)
    db.commit()


# --- Shift Assignments ---
@router.get("/assignments/all", response_model=list[ShiftAssignmentOut])
def list_assignments(
    shift_id: int | None = None, db: Session = Depends(get_db)
):
    query = db.query(ShiftAssignment)
    if shift_id is not None:
        query = query.filter(ShiftAssignment.shift_id == shift_id)
    return query.all()


@router.post("/assignments", response_model=ShiftAssignmentOut, status_code=201)
def create_assignment(
    data: ShiftAssignmentCreate, db: Session = Depends(get_db)
):
    # Validate references
    if not db.query(Worker).filter(Worker.id == data.worker_id).first():
        raise HTTPException(status_code=404, detail="Worker not found")
    if not db.query(Shift).filter(Shift.id == data.shift_id).first():
        raise HTTPException(status_code=404, detail="Shift not found")
    # Prevent duplicates
    existing = (
        db.query(ShiftAssignment)
        .filter(
            ShiftAssignment.worker_id == data.worker_id,
            ShiftAssignment.shift_id == data.shift_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Assignment already exists"
        )
    assignment = ShiftAssignment(
        worker_id=data.worker_id, shift_id=data.shift_id
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = (
        db.query(ShiftAssignment)
        .filter(ShiftAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
