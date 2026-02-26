"""Tests for the schedule optimizer, focusing on batch-rotation constraints."""

from app.schemas import OptimizationRequest
from app.services.optimizer import optimize_schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workers(n: int, skill_ids: list[int] | None = None):
    """Create *n* workers, all sharing the same skills."""
    sids = skill_ids or []
    return [
        {"id": i + 1, "name": f"T{i + 1}", "skill_ids": sids}
        for i in range(n)
    ]


def _make_stations(specs: list[tuple[str, int, int]]):
    """
    specs: list of (name, workers_needed, max_minutes_per_worker).
    All stations require no special skills.
    """
    return [
        {
            "id": i + 1,
            "name": name,
            "workers_needed": needed,
            "max_minutes_per_worker": max_min,
            "required_skill_ids": [],
        }
        for i, (name, needed, max_min) in enumerate(specs)
    ]


def _check_destination_grouping(result, rotation_group_size: int):
    """
    Verify that for every transition t→t+1, the flow from any station
    A to any different station B is 0 or a multiple of rotation_group_size.
    Returns a list of violation descriptions (empty = pass).
    """
    violations: list[str] = []
    schedule = result.schedule
    for t in range(len(schedule) - 1):
        slot_a = schedule[t]
        slot_b = schedule[t + 1]

        # Build station-of-worker maps
        worker_station_a: dict[int, str] = {}
        worker_station_b: dict[int, str] = {}
        for assign in slot_a.assignments:
            for wid in assign.worker_ids:
                worker_station_a[wid] = assign.station_name
        for assign in slot_b.assignments:
            for wid in assign.worker_ids:
                worker_station_b[wid] = assign.station_name

        # Count flows between every pair of distinct stations
        from collections import Counter
        flow: Counter[tuple[str, str]] = Counter()
        for wid, src in worker_station_a.items():
            dst = worker_station_b.get(wid)
            if dst and dst != src:
                flow[(src, dst)] += 1

        for (src, dst), count in flow.items():
            if count % rotation_group_size != 0:
                violations.append(
                    f"Slot {t}→{t+1}: flow {src}→{dst} = {count} "
                    f"(not a multiple of {rotation_group_size})"
                )

    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_destination_grouping_basic():
    """
    5 stations (2, 4, 2, 4, 2 workers), 14 workers, group_size=2.
    Every inter-station flow must be 0 or 2 (or 4, etc.).
    Use generous max_minutes so the problem is feasible.
    """
    stations = _make_stations([
        ("CORTE", 2, 480),
        ("LIMPIEZA", 4, 480),
        ("COCINADO", 2, 480),
        ("EMPAQUETADO", 4, 480),
        ("PARALELO", 2, 480),
    ])
    workers = _make_workers(14)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=2,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=480,
        shift_start_minutes=360,
    )

    assert result.status in ("optimal", "feasible"), (
        f"Solver returned {result.status}: {result.message}"
    )
    violations = _check_destination_grouping(result, 2)
    assert violations == [], (
        "Destination-grouping violated:\n" + "\n".join(violations)
    )


def test_destination_grouping_group4():
    """
    Two 4-worker stations, group_size=4.
    Workers can only swap as a full block of 4.
    """
    stations = _make_stations([
        ("A", 4, 120),
        ("B", 4, 120),
    ])
    workers = _make_workers(8)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=4,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=240,
        shift_start_minutes=0,
    )

    assert result.status in ("optimal", "feasible")
    violations = _check_destination_grouping(result, 4)
    assert violations == [], (
        "Destination-grouping violated:\n" + "\n".join(violations)
    )


def test_turnover_constraint():
    """
    Verify the turnover at each station (total leaving) is also
    a multiple of rotation_group_size.
    """
    stations = _make_stations([
        ("CORTE", 2, 480),
        ("LIMPIEZA", 4, 480),
        ("COCINADO", 2, 480),
        ("EMPAQUETADO", 4, 480),
        ("PARALELO", 2, 480),
    ])
    workers = _make_workers(14)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=2,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=480,
        shift_start_minutes=360,
    )
    assert result.status in ("optimal", "feasible")

    schedule = result.schedule
    for t in range(len(schedule) - 1):
        slot_a = schedule[t]
        slot_b = schedule[t + 1]
        for assign_a in slot_a.assignments:
            ids_a = set(assign_a.worker_ids)
            # Find same station in next slot
            ids_b = set()
            for assign_b in slot_b.assignments:
                if assign_b.station_id == assign_a.station_id:
                    ids_b = set(assign_b.worker_ids)
                    break
            leaving = ids_a - ids_b
            assert len(leaving) % 2 == 0, (
                f"Slot {t}→{t+1}: {assign_a.station_name} lost "
                f"{len(leaving)} worker(s), not a multiple of 2"
            )


def test_small_station_locked_with_large_group():
    """
    Station with 2 workers + group_size=4 → workers locked in place.
    Use enough workers and relaxed max_minutes for feasibility.
    """
    stations = _make_stations([
        ("SMALL", 2, 480),
        ("BIG", 4, 480),
    ])
    workers = _make_workers(8)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=4,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=240,
        shift_start_minutes=0,
    )
    assert result.status in ("optimal", "feasible"), (
        f"Solver returned {result.status}: {result.message}\n"
        f"Diagnostics: {result.diagnostics}"
    )

    # SMALL station must have the same 2 workers every slot
    small_ids = None
    for slot in result.schedule:
        for assign in slot.assignments:
            if assign.station_name == "SMALL":
                current = set(assign.worker_ids)
                if small_ids is None:
                    small_ids = current
                else:
                    assert current == small_ids, (
                        f"SMALL station workers changed: "
                        f"{small_ids} → {current}"
                    )


def test_destination_grouping_tight():
    """
    3 stations (2, 2, 2 workers), 6 workers, group_size=2, short max_minutes.
    Forces rotation and every flow must be a multiple of 2.
    """
    stations = _make_stations([
        ("A", 2, 120),
        ("B", 2, 120),
        ("C", 2, 120),
    ])
    workers = _make_workers(6)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=2,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=360,
        shift_start_minutes=0,
    )

    assert result.status in ("optimal", "feasible"), (
        f"Solver returned {result.status}: {result.message}"
    )
    violations = _check_destination_grouping(result, 2)
    assert violations == [], (
        "Destination-grouping violated:\n" + "\n".join(violations)
    )
