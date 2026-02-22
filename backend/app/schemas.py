from pydantic import BaseModel


# --- Skills ---
class SkillBase(BaseModel):
    name: str
    description: str = ""


class SkillCreate(SkillBase):
    pass


class SkillOut(SkillBase):
    id: int

    model_config = {"from_attributes": True}


# --- Workers ---
class WorkerBase(BaseModel):
    name: str
    active: bool = True


class WorkerCreate(WorkerBase):
    skill_ids: list[int] = []


class WorkerUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
    skill_ids: list[int] | None = None


class WorkerOut(WorkerBase):
    id: int
    skills: list[SkillOut] = []

    model_config = {"from_attributes": True}


# --- Shifts ---
class ShiftBase(BaseModel):
    name: str
    start_hour: float
    end_hour: float
    active: bool = True


class ShiftCreate(ShiftBase):
    pass


class ShiftOut(ShiftBase):
    id: int

    model_config = {"from_attributes": True}


# --- Shift Assignments ---
class ShiftAssignmentCreate(BaseModel):
    worker_id: int
    shift_id: int


class ShiftAssignmentOut(BaseModel):
    id: int
    worker_id: int
    shift_id: int
    worker: WorkerOut
    shift: ShiftOut

    model_config = {"from_attributes": True}


# --- Stations ---
class StationBase(BaseModel):
    name: str
    production_line_id: int
    position: int
    workers_needed: int = 1
    max_minutes_per_worker: int = 120
    cycle_time_minutes: float = 1.0
    active: bool = True


class StationCreate(StationBase):
    required_skill_ids: list[int] = []


class StationUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    workers_needed: int | None = None
    max_minutes_per_worker: int | None = None
    cycle_time_minutes: float | None = None
    active: bool | None = None
    required_skill_ids: list[int] | None = None


class StationOut(StationBase):
    id: int
    required_skills: list[SkillOut] = []

    model_config = {"from_attributes": True}


# --- Production Lines ---
class ProductionLineBase(BaseModel):
    name: str
    description: str = ""
    active: bool = True


class ProductionLineCreate(ProductionLineBase):
    pass


class ProductionLineOut(ProductionLineBase):
    id: int
    stations: list[StationOut] = []

    model_config = {"from_attributes": True}


# --- Optimization ---
class OptimizationRequest(BaseModel):
    production_line_id: int
    shift_id: int
    slot_duration_minutes: int = 30  # Length of each rotation slot


class StationAssignment(BaseModel):
    station_id: int
    station_name: str
    worker_ids: list[int]
    worker_names: list[str]


class TimeSlot(BaseModel):
    slot_index: int
    start_minutes: int
    end_minutes: int
    assignments: list[StationAssignment]


class OptimizationResult(BaseModel):
    production_line_id: int
    shift_id: int
    slot_duration_minutes: int
    total_slots: int
    schedule: list[TimeSlot]
    unassigned_slots: list[dict] = []
    status: str  # "optimal", "feasible", "infeasible"
    message: str = ""
