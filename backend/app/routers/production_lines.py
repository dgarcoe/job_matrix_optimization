from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import ProductionLine, Skill, Station
from app.schemas import (
    ProductionLineCreate,
    ProductionLineOut,
    StationCreate,
    StationOut,
    StationUpdate,
)

router = APIRouter(prefix="/api/production-lines", tags=["production_lines"])


# --- Production Lines ---
@router.get("", response_model=list[ProductionLineOut])
def list_production_lines(db: Session = Depends(get_db)):
    return db.query(ProductionLine).all()


@router.post("", response_model=ProductionLineOut, status_code=201)
def create_production_line(
    data: ProductionLineCreate, db: Session = Depends(get_db)
):
    line = ProductionLine(
        name=data.name, description=data.description, active=data.active
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.get("/{line_id}", response_model=ProductionLineOut)
def get_production_line(line_id: int, db: Session = Depends(get_db)):
    line = (
        db.query(ProductionLine)
        .filter(ProductionLine.id == line_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    return line


@router.put("/{line_id}", response_model=ProductionLineOut)
def update_production_line(
    line_id: int, data: ProductionLineCreate, db: Session = Depends(get_db)
):
    line = (
        db.query(ProductionLine)
        .filter(ProductionLine.id == line_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    line.name = data.name
    line.description = data.description
    line.active = data.active
    db.commit()
    db.refresh(line)
    return line


@router.delete("/{line_id}", status_code=204)
def delete_production_line(line_id: int, db: Session = Depends(get_db)):
    line = (
        db.query(ProductionLine)
        .filter(ProductionLine.id == line_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    db.delete(line)
    db.commit()


# --- Stations ---
@router.post("/{line_id}/stations", response_model=StationOut, status_code=201)
def create_station(
    line_id: int, data: StationCreate, db: Session = Depends(get_db)
):
    line = (
        db.query(ProductionLine)
        .filter(ProductionLine.id == line_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Production line not found")
    station = Station(
        name=data.name,
        production_line_id=line_id,
        position=data.position,
        workers_needed=data.workers_needed,
        max_minutes_per_worker=data.max_minutes_per_worker,
        cycle_time_minutes=data.cycle_time_minutes,
        active=data.active,
    )
    if data.required_skill_ids:
        skills = (
            db.query(Skill).filter(Skill.id.in_(data.required_skill_ids)).all()
        )
        station.required_skills = skills
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@router.put(
    "/{line_id}/stations/{station_id}", response_model=StationOut
)
def update_station(
    line_id: int,
    station_id: int,
    data: StationUpdate,
    db: Session = Depends(get_db),
):
    station = (
        db.query(Station)
        .filter(Station.id == station_id, Station.production_line_id == line_id)
        .first()
    )
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    if data.name is not None:
        station.name = data.name
    if data.position is not None:
        station.position = data.position
    if data.workers_needed is not None:
        station.workers_needed = data.workers_needed
    if data.max_minutes_per_worker is not None:
        station.max_minutes_per_worker = data.max_minutes_per_worker
    if data.cycle_time_minutes is not None:
        station.cycle_time_minutes = data.cycle_time_minutes
    if data.active is not None:
        station.active = data.active
    if data.required_skill_ids is not None:
        skills = (
            db.query(Skill).filter(Skill.id.in_(data.required_skill_ids)).all()
        )
        station.required_skills = skills
    db.commit()
    db.refresh(station)
    return station


@router.delete("/{line_id}/stations/{station_id}", status_code=204)
def delete_station(
    line_id: int, station_id: int, db: Session = Depends(get_db)
):
    station = (
        db.query(Station)
        .filter(Station.id == station_id, Station.production_line_id == line_id)
        .first()
    )
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    db.delete(station)
    db.commit()
