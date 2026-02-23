"""
Production line schedule optimizer using Google OR-Tools.

Given a production line, a shift, and available workers, this optimizer
assigns workers to stations across time slots such that:
  - Each station gets the required number of workers per slot.
  - Workers only get assigned to stations they have skills for.
  - No worker exceeds the maximum allowed time at any single station.
  - Workers are rotated across stations to distribute workload.
"""

import math

from ortools.sat.python import cp_model

from app.schemas import (
    DiagnosticItem,
    OptimizationRequest,
    OptimizationResult,
    StationAssignment,
    TimeSlot,
)


def _run_diagnostics(
    workers: list[dict],
    stations: list[dict],
    slot_duration: int,
    num_slots: int,
) -> list[DiagnosticItem]:
    """Check for common causes of infeasibility and return diagnostic items."""
    diagnostics: list[DiagnosticItem] = []
    num_workers = len(workers)

    # Total simultaneous workers required across all stations
    total_needed = sum(s["workers_needed"] for s in stations)
    if num_workers < total_needed:
        diagnostics.append(
            DiagnosticItem(
                level="error",
                message=(
                    f"Not enough workers: {num_workers} available but "
                    f"{total_needed} needed simultaneously across all stations."
                ),
            )
        )

    # Per-station checks
    for s in stations:
        required_skills = set(s["required_skill_ids"])
        eligible_count = 0
        for w in workers:
            w_skills = set(w["skill_ids"])
            if not required_skills or required_skills.issubset(w_skills):
                eligible_count += 1

        needed = s["workers_needed"]

        # Check: enough eligible workers to fill the station at all?
        if eligible_count < needed:
            skill_names = ", ".join(str(sid) for sid in s["required_skill_ids"])
            diagnostics.append(
                DiagnosticItem(
                    level="error",
                    station_name=s["name"],
                    message=(
                        f"Station '{s['name']}' needs {needed} worker(s) "
                        f"but only {eligible_count} worker(s) have the "
                        f"required skill(s) (IDs: {skill_names or 'none'})."
                    ),
                )
            )
        else:
            # Check: enough eligible workers for rotation given max_minutes?
            max_slots = s["max_minutes_per_worker"] // slot_duration
            if max_slots > 0 and max_slots < num_slots:
                rotations_needed = math.ceil(num_slots / max_slots)
                min_unique = rotations_needed * needed
                if eligible_count < min_unique:
                    diagnostics.append(
                        DiagnosticItem(
                            level="error",
                            station_name=s["name"],
                            message=(
                                f"Station '{s['name']}' needs {needed} worker(s) "
                                f"per slot, max {s['max_minutes_per_worker']} min "
                                f"per worker ({max_slots} slots). Over {num_slots} "
                                f"slots this requires at least {min_unique} eligible "
                                f"worker(s), but only {eligible_count} qualify."
                            ),
                        )
                    )

    return diagnostics


def optimize_schedule(
    request: OptimizationRequest,
    workers: list[dict],
    stations: list[dict],
    shift_duration_minutes: int,
) -> OptimizationResult:
    """
    Build and solve a constraint-programming model for worker rotation.

    Args:
        request: The optimization parameters.
        workers: List of dicts with keys: id, name, skill_ids.
        stations: List of dicts with keys: id, name, workers_needed,
                  max_minutes_per_worker, required_skill_ids.
        shift_duration_minutes: Total shift length in minutes.

    Returns:
        OptimizationResult with the full schedule.
    """
    slot_duration = request.slot_duration_minutes
    num_slots = shift_duration_minutes // slot_duration

    if num_slots == 0:
        return OptimizationResult(
            production_line_id=request.production_line_id,
            shift_id=request.shift_id,
            slot_duration_minutes=slot_duration,
            total_slots=0,
            schedule=[],
            status="infeasible",
            message="Shift duration is shorter than slot duration.",
        )

    # Pre-compute eligibility: can worker w work at station s?
    worker_ids = [w["id"] for w in workers]
    station_ids = [s["id"] for s in stations]

    worker_idx = {wid: i for i, wid in enumerate(worker_ids)}
    station_idx = {sid: i for i, sid in enumerate(station_ids)}

    num_workers = len(workers)
    num_stations = len(stations)

    eligible = [[False] * num_stations for _ in range(num_workers)]
    for wi, w in enumerate(workers):
        w_skills = set(w["skill_ids"])
        for si, s in enumerate(stations):
            required = set(s["required_skill_ids"])
            # If station requires no skills, anyone can work there.
            # Otherwise worker must have all required skills.
            if not required or required.issubset(w_skills):
                eligible[wi][si] = True

    # Max slots a worker can spend at a single station
    max_slots_at_station = {}
    for si, s in enumerate(stations):
        max_slots_at_station[si] = s["max_minutes_per_worker"] // slot_duration

    # --- Build CP-SAT model ---
    model = cp_model.CpModel()

    # Decision variables: x[w][s][t] = 1 if worker w is at station s in slot t
    x = {}
    for wi in range(num_workers):
        for si in range(num_stations):
            for t in range(num_slots):
                if eligible[wi][si]:
                    x[(wi, si, t)] = model.new_bool_var(f"x_w{wi}_s{si}_t{t}")
                else:
                    # Worker cannot be assigned here
                    x[(wi, si, t)] = model.new_constant(0)

    # Constraint 1: Each station must have exactly workers_needed per slot
    for si, s in enumerate(stations):
        for t in range(num_slots):
            model.add(
                sum(x[(wi, si, t)] for wi in range(num_workers))
                == s["workers_needed"]
            )

    # Constraint 2: Each worker is at most at one station per slot
    for wi in range(num_workers):
        for t in range(num_slots):
            model.add(
                sum(x[(wi, si, t)] for si in range(num_stations)) <= 1
            )

    # Constraint 3: No worker exceeds max time at any single station
    for wi in range(num_workers):
        for si in range(num_stations):
            max_s = max_slots_at_station[si]
            if max_s < num_slots:
                model.add(
                    sum(x[(wi, si, t)] for t in range(num_slots)) <= max_s
                )

    # Objective: Maximize rotation diversity.
    # We want to spread workers across stations. Minimize the max slots
    # any single worker spends at a single station by using an auxiliary
    # variable approach, but for simplicity we maximize total assignments
    # (since constraints already enforce staffing) and add a secondary
    # objective to favor balanced distribution.
    #
    # Approach: minimize the total squared concentration. Since CP-SAT
    # doesn't support quadratic directly, we minimize the sum of
    # per-worker-per-station assignment counts, weighted to favor balance.
    # Specifically: maximize the number of distinct (worker, station) pairs
    # that have at least one assignment (this promotes rotation).

    # Indicator: y[w][s] = 1 if worker w is ever assigned to station s
    y = {}
    for wi in range(num_workers):
        for si in range(num_stations):
            if eligible[wi][si]:
                y[(wi, si)] = model.new_bool_var(f"y_w{wi}_s{si}")
                # Link y to x: y=1 iff sum_t x[w][s][t] >= 1
                total = sum(x[(wi, si, t)] for t in range(num_slots))
                model.add(total >= 1).only_enforce_if(y[(wi, si)])
                model.add(total == 0).only_enforce_if(y[(wi, si)].negated())
            else:
                y[(wi, si)] = model.new_constant(0)

    # Maximize distinct assignments (promotes rotation)
    model.maximize(
        sum(y[(wi, si)] for wi in range(num_workers) for si in range(num_stations))
    )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        diagnostics = _run_diagnostics(workers, stations, slot_duration, num_slots)
        return OptimizationResult(
            production_line_id=request.production_line_id,
            shift_id=request.shift_id,
            slot_duration_minutes=slot_duration,
            total_slots=num_slots,
            schedule=[],
            diagnostics=diagnostics,
            status="infeasible",
            message=(
                "No feasible schedule found. Check that you have enough "
                "skilled workers for all stations."
            ),
        )

    status_name = "optimal" if status == cp_model.OPTIMAL else "feasible"

    # Extract schedule
    schedule: list[TimeSlot] = []
    for t in range(num_slots):
        assignments: list[StationAssignment] = []
        for si, s in enumerate(stations):
            assigned_workers = []
            assigned_names = []
            for wi, w in enumerate(workers):
                if solver.value(x[(wi, si, t)]) == 1:
                    assigned_workers.append(w["id"])
                    assigned_names.append(w["name"])
            assignments.append(
                StationAssignment(
                    station_id=s["id"],
                    station_name=s["name"],
                    worker_ids=assigned_workers,
                    worker_names=assigned_names,
                )
            )
        schedule.append(
            TimeSlot(
                slot_index=t,
                start_minutes=t * slot_duration,
                end_minutes=(t + 1) * slot_duration,
                assignments=assignments,
            )
        )

    return OptimizationResult(
        production_line_id=request.production_line_id,
        shift_id=request.shift_id,
        slot_duration_minutes=slot_duration,
        total_slots=num_slots,
        schedule=schedule,
        status=status_name,
        message=f"Schedule generated with {num_slots} time slots.",
    )
