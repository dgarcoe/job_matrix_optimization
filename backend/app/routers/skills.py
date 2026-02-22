from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Skill
from app.schemas import SkillCreate, SkillOut

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    return db.query(Skill).all()


@router.post("", response_model=SkillOut, status_code=201)
def create_skill(data: SkillCreate, db: Session = Depends(get_db)):
    skill = Skill(name=data.name, description=data.description)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.put("/{skill_id}", response_model=SkillOut)
def update_skill(skill_id: int, data: SkillCreate, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.name = data.name
    skill.description = data.description
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()
