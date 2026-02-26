"""
Production line schedule optimizer using Google OR-Tools.

Given a production line, a shift, and available workers, this optimizer
assigns workers to stations across time slots such that:
  - Each station gets the required number of workers per slot.
  - Workers only get assigned to stations they have skills for.
  - No worker exceeds the maximum allowed time at any single station.
  - Workers are rotated across stations to distribute workload.

When rotation_group_size > 1 the optimizer forms fixed *teams* of that
size.  All members of a team are always assigned to the same station and
rotate together as a unit.
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
    rotation_group_size: int = 1,
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

    # Team-model divisibility checks
    if rotation_group_size > 1:
        if num_workers % rotation_group_size != 0:
            diagnostics.append(
                DiagnosticItem(
                    level="error",
                    message=(
                        f"Number of workers ({num_workers}) is not a multiple "
                        f"of rotation group size ({rotation_group_size}). "
                        f"Cannot form complete teams."
                    ),
                )
            )

        for s in stations:
            needed = s["workers_needed"]
            if needed % rotation_group_size != 0:
                diagnostics.append(
                    DiagnosticItem(
                        level="error",
                        station_name=s["name"],
                        message=(
                            f"Station '{s['name']}' needs {needed} worker(s), "
                            f"which is not a multiple of rotation group size "
                            f"{rotation_group_size}. Cannot assign complete teams."
                        ),
                    )
                )

    return diagnostics


def optimize_schedule(
    request: OptimizationRequest,
    workers: list[dict],
    stations: list[dict],
    shift_duration_minutes: int,
    shift_start_minutes: int = 0,
) -> OptimizationResult:
    """
    Build and solve a constraint-programming model for worker rotation.

    Args:
        request: The optimization parameters.
        workers: List of dicts with keys: id, name, skill_ids.
        stations: List of dicts with keys: id, name, workers_needed,
                  max_minutes_per_worker, required_skill_ids.
        shift_duration_minutes: Total shift length in minutes.
        shift_start_minutes: Shift start as minutes from midnight, used
            to express time-slot boundaries in absolute clock time.

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
    num_workers = len(workers)
    num_stations = len(stations)

    eligible = [[False] * num_stations for _ in range(num_workers)]
    for wi, w in enumerate(workers):
        w_skills = set(w["skill_ids"])
        for si, s in enumerate(stations):
            required = set(s["required_skill_ids"])
            if not required or required.issubset(w_skills):
                eligible[wi][si] = True

    # Max slots a worker can spend at a single station
    max_slots_at_station = {}
    for si, s in enumerate(stations):
        max_slots_at_station[si] = s["max_minutes_per_worker"] // slot_duration

    rotation_group_size = request.rotation_group_size

    if rotation_group_size > 1:
        result = _solve_team_model(
            request,
            workers,
            stations,
            eligible,
            max_slots_at_station,
            num_workers,
            num_stations,
            num_slots,
            slot_duration,
            shift_start_minutes,
            rotation_group_size,
        )
    else:
        result = _solve_individual_model(
            request,
            workers,
            stations,
            eligible,
            max_slots_at_station,
            num_workers,
            num_stations,
            num_slots,
            slot_duration,
            shift_start_minutes,
        )

    return result


# ------------------------------------------------------------------
# Individual model (rotation_group_size == 1)
# ------------------------------------------------------------------


def _solve_individual_model(
    request,
    workers,
    stations,
    eligible,
    max_slots_at_station,
    num_workers,
    num_stations,
    num_slots,
    slot_duration,
    shift_start_minutes,
):
    model = cp_model.CpModel()

    # Decision variables: x[w, s, t] = 1 if worker w at station s in slot t
    x = {}
    for wi in range(num_workers):
        for si in range(num_stations):
            for t in range(num_slots):
                if eligible[wi][si]:
                    x[(wi, si, t)] = model.new_bool_var(
                        f"x_w{wi}_s{si}_t{t}"
                    )
                else:
                    x[(wi, si, t)] = model.new_constant(0)

    # C1: Station coverage
    for si, s in enumerate(stations):
        for t in range(num_slots):
            model.add(
                sum(x[(wi, si, t)] for wi in range(num_workers))
                == s["workers_needed"]
            )

    # C2: Each worker at most one station per slot
    for wi in range(num_workers):
        for t in range(num_slots):
            model.add(
                sum(x[(wi, si, t)] for si in range(num_stations)) <= 1
            )

    # C3: Max time per worker at any station
    for wi in range(num_workers):
        for si in range(num_stations):
            max_s = max_slots_at_station[si]
            if max_s < num_slots:
                model.add(
                    sum(x[(wi, si, t)] for t in range(num_slots)) <= max_s
                )

    # Objective: maximize distinct (worker, station) pairs
    y = {}
    for wi in range(num_workers):
        for si in range(num_stations):
            if eligible[wi][si]:
                y[(wi, si)] = model.new_bool_var(f"y_w{wi}_s{si}")
                total = sum(x[(wi, si, t)] for t in range(num_slots))
                model.add(total >= 1).only_enforce_if(y[(wi, si)])
                model.add(total == 0).only_enforce_if(y[(wi, si)].negated())
            else:
                y[(wi, si)] = model.new_constant(0)

    model.maximize(
        sum(
            y[(wi, si)]
            for wi in range(num_workers)
            for si in range(num_stations)
        )
    )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        diagnostics = _run_diagnostics(
            workers, stations, slot_duration, num_slots
        )
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
                start_minutes=shift_start_minutes + t * slot_duration,
                end_minutes=shift_start_minutes + (t + 1) * slot_duration,
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


# ------------------------------------------------------------------
# Team-based model (rotation_group_size > 1)
# ------------------------------------------------------------------


def _solve_team_model(
    request,
    workers,
    stations,
    eligible,
    max_slots_at_station,
    num_workers,
    num_stations,
    num_slots,
    slot_duration,
    shift_start_minutes,
    rotation_group_size,
):
    # Pre-checks: divisibility
    if num_workers % rotation_group_size != 0:
        diagnostics = _run_diagnostics(
            workers, stations, slot_duration, num_slots, rotation_group_size
        )
        return OptimizationResult(
            production_line_id=request.production_line_id,
            shift_id=request.shift_id,
            slot_duration_minutes=slot_duration,
            total_slots=num_slots,
            schedule=[],
            diagnostics=diagnostics,
            status="infeasible",
            message=(
                f"Cannot form teams: {num_workers} workers is not "
                f"a multiple of group size {rotation_group_size}."
            ),
        )

    for s in stations:
        if s["workers_needed"] % rotation_group_size != 0:
            diagnostics = _run_diagnostics(
                workers, stations, slot_duration, num_slots,
                rotation_group_size,
            )
            return OptimizationResult(
                production_line_id=request.production_line_id,
                shift_id=request.shift_id,
                slot_duration_minutes=slot_duration,
                total_slots=num_slots,
                schedule=[],
                diagnostics=diagnostics,
                status="infeasible",
                message=(
                    f"Station '{s['name']}' needs {s['workers_needed']} "
                    f"worker(s), not a multiple of group size "
                    f"{rotation_group_size}."
                ),
            )

    num_teams = num_workers // rotation_group_size
    teams_needed = {
        si: s["workers_needed"] // rotation_group_size
        for si, s in enumerate(stations)
    }

    model = cp_model.CpModel()

    # --- Variables ---

    # team[wi, g] = 1 iff worker wi belongs to team g
    team = {}
    for wi in range(num_workers):
        for g in range(num_teams):
            team[(wi, g)] = model.new_bool_var(f"tm_w{wi}_g{g}")

    # gs[g, si, t] = 1 iff team g is at station si in slot t
    gs = {}
    for g in range(num_teams):
        for si in range(num_stations):
            for t in range(num_slots):
                gs[(g, si, t)] = model.new_bool_var(f"gs_g{g}_s{si}_t{t}")

    # --- Constraints ---

    # C1: Each worker in exactly one team
    for wi in range(num_workers):
        model.add(sum(team[(wi, g)] for g in range(num_teams)) == 1)

    # C2: Each team has exactly rotation_group_size members
    for g in range(num_teams):
        model.add(
            sum(team[(wi, g)] for wi in range(num_workers))
            == rotation_group_size
        )

    # C3: Each team at most one station per slot
    for g in range(num_teams):
        for t in range(num_slots):
            model.add(
                sum(gs[(g, si, t)] for si in range(num_stations)) <= 1
            )

    # C4: Station coverage (each station needs the right number of teams)
    for si in range(num_stations):
        for t in range(num_slots):
            model.add(
                sum(gs[(g, si, t)] for g in range(num_teams))
                == teams_needed[si]
            )

    # C5: Team eligibility — if any member is ineligible at a station,
    #     the team cannot be assigned there.
    for wi in range(num_workers):
        for si in range(num_stations):
            if not eligible[wi][si]:
                for g in range(num_teams):
                    model.add(
                        sum(gs[(g, si, t)] for t in range(num_slots)) == 0
                    ).only_enforce_if(team[(wi, g)])

    # C6: Max time per team at any single station
    for g in range(num_teams):
        for si in range(num_stations):
            max_s = max_slots_at_station[si]
            if max_s < num_slots:
                model.add(
                    sum(gs[(g, si, t)] for t in range(num_slots)) <= max_s
                )

    # Symmetry breaking: restrict which teams early-indexed workers
    # can join.  Worker wi (for wi < num_teams) can only be in
    # teams 0 … wi, which anchors team numbering and avoids
    # equivalent relabellings.
    for wi in range(min(num_teams, num_workers)):
        for g in range(wi + 1, num_teams):
            model.add(team[(wi, g)] == 0)

    # --- Objective: maximize distinct (team, station) pairs ---
    y = {}
    for g in range(num_teams):
        for si in range(num_stations):
            y[(g, si)] = model.new_bool_var(f"y_g{g}_s{si}")
            total = sum(gs[(g, si, t)] for t in range(num_slots))
            model.add(total >= 1).only_enforce_if(y[(g, si)])
            model.add(total == 0).only_enforce_if(y[(g, si)].negated())

    model.maximize(
        sum(
            y[(g, si)]
            for g in range(num_teams)
            for si in range(num_stations)
        )
    )

    # --- Solve ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        diagnostics = _run_diagnostics(
            workers, stations, slot_duration, num_slots, rotation_group_size
        )
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

    # --- Extract schedule ---

    # Build team membership map
    team_members: dict[int, list[int]] = {g: [] for g in range(num_teams)}
    for g in range(num_teams):
        for wi in range(num_workers):
            if solver.value(team[(wi, g)]) == 1:
                team_members[g].append(wi)

    schedule: list[TimeSlot] = []
    for t in range(num_slots):
        assignments: list[StationAssignment] = []
        for si, s in enumerate(stations):
            assigned_workers: list[int] = []
            assigned_names: list[str] = []
            for g in range(num_teams):
                if solver.value(gs[(g, si, t)]) == 1:
                    for wi in team_members[g]:
                        assigned_workers.append(workers[wi]["id"])
                        assigned_names.append(workers[wi]["name"])
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
                start_minutes=shift_start_minutes + t * slot_duration,
                end_minutes=shift_start_minutes + (t + 1) * slot_duration,
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
