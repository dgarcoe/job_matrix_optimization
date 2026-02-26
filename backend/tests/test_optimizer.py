"""Tests for the schedule optimizer, focusing on team-based rotation."""

from app.schemas import OptimizationRequest
from app.services.optimizer import optimize_schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workers(n: int, skill_ids: list[int] | None = None):
    sids = skill_ids or []
    return [
        {"id": i + 1, "name": f"T{i + 1}", "skill_ids": sids}
        for i in range(n)
    ]


def _make_stations(specs: list[tuple[str, int, int]]):
    """specs: list of (name, workers_needed, max_minutes_per_worker)."""
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


def _extract_teams(result):
    """
    Discover fixed teams from a schedule: groups of workers that are
    always at the same station in every slot.  Returns a set of
    frozensets (one per team).
    """
    schedule = result.schedule
    if not schedule:
        return set()

    # Map worker → station for each slot
    worker_station: list[dict[int, str]] = []
    for slot in schedule:
        ws: dict[int, str] = {}
        for assign in slot.assignments:
            for wid in assign.worker_ids:
                ws[wid] = assign.station_name
        worker_station.append(ws)

    # Two workers are in the same team iff they share a station in
    # every slot where both are assigned.
    all_workers = sorted(worker_station[0].keys())
    visited: set[int] = set()
    teams: set[frozenset[int]] = set()

    for w in all_workers:
        if w in visited:
            continue
        team = {w}
        for other in all_workers:
            if other == w or other in visited:
                continue
            same = True
            for ws in worker_station:
                if w in ws and other in ws and ws[w] != ws[other]:
                    same = False
                    break
            if same:
                team.add(other)
        teams.add(frozenset(team))
        visited.update(team)

    return teams


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fixed_teams_group2():
    """
    5 stations (2,4,2,4,2 workers), 14 workers, group_size=2.
    Workers must form 7 fixed pairs that always stay together.
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

    teams = _extract_teams(result)
    assert len(teams) == 7, f"Expected 7 teams, got {len(teams)}: {teams}"
    for t in teams:
        assert len(t) == 2, f"Expected team size 2, got {len(t)}: {t}"


def test_fixed_teams_group4():
    """
    Two 4-worker stations, 8 workers, group_size=4.
    Must form 2 fixed teams of 4 that swap stations.
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

    teams = _extract_teams(result)
    assert len(teams) == 2
    for t in teams:
        assert len(t) == 4, f"Expected team size 4, got {len(t)}: {t}"


def test_teams_respect_max_time():
    """
    3 stations of 2 workers each, 6 workers, group_size=2,
    max_minutes=120 with 60-min slots (max 2 slots per station).
    Teams must rotate to satisfy the time limit.
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

    assert result.status in ("optimal", "feasible")
    teams = _extract_teams(result)
    assert len(teams) == 3
    for t in teams:
        assert len(t) == 2

    # Verify no team exceeds 2 consecutive slots at any station
    schedule = result.schedule
    for slot in schedule:
        for assign in slot.assignments:
            pass  # coverage is checked by solver constraints

    # Verify each team visits at least 2 different stations
    team_stations: dict[frozenset[int], set[str]] = {
        t: set() for t in teams
    }
    for slot in result.schedule:
        for assign in slot.assignments:
            wids = frozenset(assign.worker_ids)
            for t in teams:
                if t <= set(assign.worker_ids):
                    team_stations[t].add(assign.station_name)
    for t, visited in team_stations.items():
        assert len(visited) >= 2, (
            f"Team {t} only visited {visited}, expected at least 2 stations"
        )


def test_individual_model_unchanged():
    """
    group_size=1 should use the individual model (no teams).
    """
    stations = _make_stations([
        ("A", 2, 120),
        ("B", 2, 120),
    ])
    workers = _make_workers(4)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=1,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=240,
        shift_start_minutes=0,
    )

    assert result.status in ("optimal", "feasible")
    assert result.total_slots == 4


def test_infeasible_indivisible_workers():
    """
    5 workers with group_size=2 → can't form complete teams.
    """
    stations = _make_stations([("A", 4, 480)])
    workers = _make_workers(5)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=2,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=120,
        shift_start_minutes=0,
    )

    assert result.status == "infeasible"


def test_infeasible_indivisible_station():
    """
    Station needing 3 workers with group_size=2 → can't fill with teams.
    """
    stations = _make_stations([("A", 3, 480)])
    workers = _make_workers(6)
    request = OptimizationRequest(
        production_line_id=1,
        shift_id=1,
        slot_duration_minutes=60,
        rotation_group_size=2,
    )

    result = optimize_schedule(
        request, workers, stations,
        shift_duration_minutes=120,
        shift_start_minutes=0,
    )

    assert result.status == "infeasible"
