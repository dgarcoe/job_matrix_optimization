export interface Skill {
  id: number;
  name: string;
  description: string;
}

export interface Worker {
  id: number;
  name: string;
  active: boolean;
  skills: Skill[];
}

export interface Shift {
  id: number;
  name: string;
  start_hour: number;
  end_hour: number;
  active: boolean;
}

export interface ShiftAssignment {
  id: number;
  worker_id: number;
  shift_id: number;
  worker: Worker;
  shift: Shift;
}

export interface Station {
  id: number;
  name: string;
  production_line_id: number;
  position: number;
  workers_needed: number;
  max_minutes_per_worker: number;
  cycle_time_minutes: number;
  active: boolean;
  required_skills: Skill[];
  layout_x: number;
  layout_y: number;
}

export interface StationConnection {
  id: number;
  production_line_id: number;
  source_station_id: number;
  target_station_id: number;
  label: string;
}

export interface ProductionLine {
  id: number;
  name: string;
  description: string;
  active: boolean;
  stations: Station[];
  connections: StationConnection[];
}

export interface StationAssignment {
  station_id: number;
  station_name: string;
  worker_ids: number[];
  worker_names: string[];
}

export interface TimeSlot {
  slot_index: number;
  start_minutes: number;
  end_minutes: number;
  assignments: StationAssignment[];
}

export interface OptimizationResult {
  production_line_id: number;
  shift_id: number;
  slot_duration_minutes: number;
  total_slots: number;
  schedule: TimeSlot[];
  status: string;
  message: string;
}
