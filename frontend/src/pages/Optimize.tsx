import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "../api/client";
import type {
  ProductionLine,
  Shift,
  OptimizationResult,
} from "../api/types";
import GanttChart from "../components/GanttChart";

function formatMinutes(m: number): string {
  const h = Math.floor(m / 60);
  const mins = m % 60;
  return `${String(h).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

export default function Optimize() {
  const { t } = useTranslation();

  const [lineId, setLineId] = useState<number | "">("");
  const [shiftId, setShiftId] = useState<number | "">("");
  const [slotDuration, setSlotDuration] = useState(30);
  const [rotationGroupSize, setRotationGroupSize] = useState(1);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: lines } = useQuery<ProductionLine[]>({
    queryKey: ["lines"],
    queryFn: () => api.get("/api/production-lines").then((r) => r.data),
  });

  const { data: shifts } = useQuery<Shift[]>({
    queryKey: ["shifts"],
    queryFn: () => api.get("/api/shifts").then((r) => r.data),
  });

  const optimizeMutation = useMutation({
    mutationFn: (data: {
      production_line_id: number;
      shift_id: number;
      slot_duration_minutes: number;
      rotation_group_size: number;
    }) => api.post("/api/optimize", data),
    onSuccess: (response) => {
      setResult(response.data);
      setError(null);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || t("common.error"));
      setResult(null);
    },
  });

  const handleOptimize = (e: React.FormEvent) => {
    e.preventDefault();
    if (lineId === "" || shiftId === "") return;
    optimizeMutation.mutate({
      production_line_id: lineId as number,
      shift_id: shiftId as number,
      slot_duration_minutes: slotDuration,
      rotation_group_size: rotationGroupSize,
    });
  };

  const statusClass =
    result?.status === "optimal"
      ? "status-optimal"
      : result?.status === "feasible"
        ? "status-feasible"
        : "status-infeasible";

  // Collect all station names for the matrix header
  const stationNames =
    result && result.schedule.length > 0
      ? result.schedule[0].assignments.map((a) => a.station_name)
      : [];

  return (
    <div>
      <h2>{t("optimize.title")}</h2>

      <form onSubmit={handleOptimize} className="form-row">
        <select
          value={lineId}
          onChange={(e) =>
            setLineId(e.target.value ? Number(e.target.value) : "")
          }
          required
        >
          <option value="">{t("optimize.select_line")}</option>
          {lines?.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
        <select
          value={shiftId}
          onChange={(e) =>
            setShiftId(e.target.value ? Number(e.target.value) : "")
          }
          required
        >
          <option value="">{t("optimize.select_shift")}</option>
          {shifts?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <label>
          {t("optimize.slot_duration")}
          <input
            type="number"
            min={5}
            max={240}
            step={5}
            value={slotDuration}
            onChange={(e) => setSlotDuration(Number(e.target.value))}
          />
        </label>
        <label>
          {t("optimize.rotation_group_size")}
          <input
            type="number"
            min={1}
            max={50}
            step={1}
            value={rotationGroupSize}
            onChange={(e) => setRotationGroupSize(Number(e.target.value))}
          />
        </label>
        <button type="submit" disabled={optimizeMutation.isPending}>
          {optimizeMutation.isPending
            ? t("common.loading")
            : t("optimize.run")}
        </button>
      </form>

      {error && <div className="error-msg">{error}</div>}

      {result && (
        <div className="optimization-result">
          <div className={`status-banner ${statusClass}`}>
            <strong>{t("optimize.status")}:</strong>{" "}
            {t(`optimize.${result.status}`)}
            {result.message && <span> - {result.message}</span>}
          </div>

          {result.diagnostics && result.diagnostics.length > 0 && (
            <div className="diagnostics-panel">
              <h3>{t("optimize.diagnostics_title")}</h3>
              <ul className="diagnostics-list">
                {result.diagnostics.map((d, i) => (
                  <li key={i} className={`diagnostic-item diagnostic-${d.level}`}>
                    <span className="diagnostic-icon">
                      {d.level === "error" ? "\u2718" : "\u26A0"}
                    </span>
                    <span>{d.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.schedule.length > 0 && (
            <>
              <h3>{t("optimize.schedule")}</h3>
              <div className="schedule-table-wrapper">
                <table className="schedule-table">
                  <thead>
                    <tr>
                      <th>{t("optimize.time_slot")}</th>
                      {stationNames.map((name) => (
                        <th key={name}>{name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.schedule.map((slot) => (
                      <tr key={slot.slot_index}>
                        <td className="time-cell">
                          {formatMinutes(slot.start_minutes)} -{" "}
                          {formatMinutes(slot.end_minutes)}
                        </td>
                        {slot.assignments.map((a) => (
                          <td key={a.station_id} className="assignment-cell">
                            {a.worker_names.length > 0
                              ? a.worker_names.join(", ")
                              : "-"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <GanttChart schedule={result.schedule} slotDuration={slotDuration} />
            </>
          )}
        </div>
      )}

      {!result && !error && (
        <p className="hint">{t("optimize.no_schedule")}</p>
      )}
    </div>
  );
}
