from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base

# Association table: worker <-> skill (many-to-many)
worker_skills = Table(
    "worker_skills",
    Base.metadata,
    Column("worker_id", Integer, ForeignKey("workers.id"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
)

# Association table: station <-> required skill (many-to-many)
station_required_skills = Table(
    "station_required_skills",
    Base.metadata,
    Column("station_id", Integer, ForeignKey("stations.id"), primary_key=True),
    Column("skill_id", Integer, ForeignKey("skills.id"), primary_key=True),
)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, default="")

    workers = relationship("Worker", secondary=worker_skills, back_populates="skills")
    stations = relationship(
        "Station", secondary=station_required_skills, back_populates="required_skills"
    )


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    skills = relationship("Skill", secondary=worker_skills, back_populates="workers")
    shift_assignments = relationship("ShiftAssignment", back_populates="worker")


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_hour = Column(Float, nullable=False)  # e.g. 6.0 = 06:00, 14.5 = 14:30
    end_hour = Column(Float, nullable=False)
    active = Column(Boolean, default=True)

    assignments = relationship("ShiftAssignment", back_populates="shift")


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)

    worker = relationship("Worker", back_populates="shift_assignments")
    shift = relationship("Shift", back_populates="assignments")


class ProductionLine(Base):
    __tablename__ = "production_lines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    active = Column(Boolean, default=True)

    stations = relationship(
        "Station", back_populates="production_line", cascade="all, delete-orphan"
    )
    connections = relationship(
        "StationConnection",
        back_populates="production_line",
        cascade="all, delete-orphan",
    )


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    production_line_id = Column(
        Integer, ForeignKey("production_lines.id"), nullable=False
    )
    position = Column(Integer, nullable=False)  # Order in the line
    workers_needed = Column(Integer, default=1)
    max_minutes_per_worker = Column(
        Integer, default=120
    )  # Max time a worker can stay here
    cycle_time_minutes = Column(Float, default=1.0)  # Time per unit/cycle
    active = Column(Boolean, default=True)

    # Layout position for visual flow editor (canvas coordinates)
    layout_x = Column(Float, default=0.0)
    layout_y = Column(Float, default=0.0)

    production_line = relationship("ProductionLine", back_populates="stations")
    required_skills = relationship(
        "Skill",
        secondary=station_required_skills,
        back_populates="stations",
    )


class StationConnection(Base):
    """Directed edge between two stations representing process flow."""

    __tablename__ = "station_connections"

    id = Column(Integer, primary_key=True, index=True)
    production_line_id = Column(
        Integer, ForeignKey("production_lines.id"), nullable=False
    )
    source_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    target_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    label = Column(String, default="")

    __table_args__ = (
        UniqueConstraint(
            "source_station_id",
            "target_station_id",
            name="uq_station_connection",
        ),
    )

    production_line = relationship("ProductionLine", back_populates="connections")
    source_station = relationship(
        "Station", foreign_keys=[source_station_id]
    )
    target_station = relationship(
        "Station", foreign_keys=[target_station_id]
    )
