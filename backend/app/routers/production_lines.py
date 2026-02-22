from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import ProductionLine, Skill, Station, StationConnection
from app.schemas import (
    ProductionLineCreate,
    ProductionLineOut,
    StationConnectionCreate,
    StationConnectionOut,
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
        layout_x=data.layout_x,
        layout_y=data.layout_y,
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
    if data.layout_x is not None:
        station.layout_x = data.layout_x
    if data.layout_y is not None:
        station.layout_y = data.layout_y
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
    # Also delete connections involving this station
    db.query(StationConnection).filter(
        (StationConnection.source_station_id == station_id)
        | (StationConnection.target_station_id == station_id)
    ).delete(synchronize_session=False)
    db.delete(station)
    db.commit()


# --- Station Connections ---
@router.get(
    "/{line_id}/connections",
    response_model=list[StationConnectionOut],
)
def list_connections(line_id: int, db: Session = Depends(get_db)):
    return (
        db.query(StationConnection)
        .filter(StationConnection.production_line_id == line_id)
        .all()
    )


@router.post(
    "/{line_id}/connections",
    response_model=StationConnectionOut,
    status_code=201,
)
def create_connection(
    line_id: int,
    data: StationConnectionCreate,
    db: Session = Depends(get_db),
):
    # Validate both stations belong to this line
    source = (
        db.query(Station)
        .filter(Station.id == data.source_station_id, Station.production_line_id == line_id)
        .first()
    )
    target = (
        db.query(Station)
        .filter(Station.id == data.target_station_id, Station.production_line_id == line_id)
        .first()
    )
    if not source or not target:
        raise HTTPException(
            status_code=400,
            detail="Source and target stations must belong to this production line",
        )
    if data.source_station_id == data.target_station_id:
        raise HTTPException(
            status_code=400, detail="Cannot connect a station to itself"
        )
    # Check for duplicate
    existing = (
        db.query(StationConnection)
        .filter(
            StationConnection.source_station_id == data.source_station_id,
            StationConnection.target_station_id == data.target_station_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Connection already exists")

    conn = StationConnection(
        production_line_id=line_id,
        source_station_id=data.source_station_id,
        target_station_id=data.target_station_id,
        label=data.label,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


@router.delete("/{line_id}/connections/{connection_id}", status_code=204)
def delete_connection(
    line_id: int, connection_id: int, db: Session = Depends(get_db)
):
    conn = (
        db.query(StationConnection)
        .filter(
            StationConnection.id == connection_id,
            StationConnection.production_line_id == line_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    db.delete(conn)
    db.commit()
