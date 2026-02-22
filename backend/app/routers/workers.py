from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Skill, Worker
from app.schemas import WorkerCreate, WorkerOut, WorkerUpdate

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.get("", response_model=list[WorkerOut])
def list_workers(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Worker)
    if active_only:
        query = query.filter(Worker.active.is_(True))
    return query.all()


@router.post("", response_model=WorkerOut, status_code=201)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    worker = Worker(name=data.name, active=data.active)
    if data.skill_ids:
        skills = db.query(Skill).filter(Skill.id.in_(data.skill_ids)).all()
        worker.skills = skills
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.put("/{worker_id}", response_model=WorkerOut)
def update_worker(
    worker_id: int, data: WorkerUpdate, db: Session = Depends(get_db)
):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if data.name is not None:
        worker.name = data.name
    if data.active is not None:
        worker.active = data.active
    if data.skill_ids is not None:
        skills = db.query(Skill).filter(Skill.id.in_(data.skill_ids)).all()
        worker.skills = skills
    db.commit()
    db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=204)
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    db.delete(worker)
    db.commit()
