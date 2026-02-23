import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { TimeSlot } from "../api/types";

interface GanttChartProps {
  schedule: TimeSlot[];
  slotDuration: number;
}

interface WorkerSlot {
  slotIndex: number;
  startMinutes: number;
  endMinutes: number;
  stationName: string;
  stationId: number;
}

const STATION_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
  "#14b8a6", // teal
  "#6366f1", // indigo
];

function formatMinutes(m: number): string {
  const h = Math.floor(m / 60);
  const mins = m % 60;
  return `${String(h).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

export default function GanttChart({ schedule }: GanttChartProps) {
  const { t } = useTranslation();

  const { workerRows, stationColorMap, totalStart, totalEnd } = useMemo(() => {
    if (schedule.length === 0)
      return { workerRows: [], stationColorMap: new Map(), totalStart: 0, totalEnd: 0 };

    // Collect unique stations in order, assign colors
    const stationMap = new Map<number, string>();
    for (const slot of schedule) {
      for (const a of slot.assignments) {
        if (!stationMap.has(a.station_id)) {
          stationMap.set(a.station_id, a.station_name);
        }
      }
    }
    const colorMap = new Map<number, string>();
    let ci = 0;
    for (const id of stationMap.keys()) {
      colorMap.set(id, STATION_COLORS[ci % STATION_COLORS.length]);
      ci++;
    }

    // Build per-worker timeline
    const workerMap = new Map<string, WorkerSlot[]>();
    for (const slot of schedule) {
      for (const a of slot.assignments) {
        for (const wName of a.worker_names) {
          if (!workerMap.has(wName)) {
            workerMap.set(wName, []);
          }
          workerMap.get(wName)!.push({
            slotIndex: slot.slot_index,
            startMinutes: slot.start_minutes,
            endMinutes: slot.end_minutes,
            stationName: a.station_name,
            stationId: a.station_id,
          });
        }
      }
    }

    // Merge consecutive slots at the same station for each worker
    const rows: { name: string; segments: WorkerSlot[] }[] = [];
    for (const [name, slots] of workerMap) {
      slots.sort((a, b) => a.slotIndex - b.slotIndex);
      const merged: WorkerSlot[] = [];
      for (const s of slots) {
        const last = merged[merged.length - 1];
        if (last && last.stationId === s.stationId && last.endMinutes === s.startMinutes) {
          last.endMinutes = s.endMinutes;
        } else {
          merged.push({ ...s });
        }
      }
      rows.push({ name, segments: merged });
    }
    rows.sort((a, b) => a.name.localeCompare(b.name));

    const tStart = schedule[0].start_minutes;
    const tEnd = schedule[schedule.length - 1].end_minutes;

    return { workerRows: rows, stationColorMap: colorMap, totalStart: tStart, totalEnd: tEnd };
  }, [schedule]);

  if (workerRows.length === 0) return null;

  const totalDuration = totalEnd - totalStart;

  // Collect legend entries
  const legend: { name: string; color: string }[] = [];
  const seen = new Set<number>();
  for (const slot of schedule) {
    for (const a of slot.assignments) {
      if (!seen.has(a.station_id)) {
        seen.add(a.station_id);
        legend.push({ name: a.station_name, color: stationColorMap.get(a.station_id) || "#999" });
      }
    }
  }

  // Time ticks
  const ticks: { minutes: number; label: string }[] = [];
  for (const slot of schedule) {
    ticks.push({ minutes: slot.start_minutes, label: formatMinutes(slot.start_minutes) });
  }
  ticks.push({
    minutes: schedule[schedule.length - 1].end_minutes,
    label: formatMinutes(schedule[schedule.length - 1].end_minutes),
  });

  return (
    <div className="gantt-container">
      <h3>{t("optimize.gantt_title")}</h3>

      <div className="gantt-legend">
        {legend.map((l) => (
          <span key={l.name} className="gantt-legend-item">
            <span className="gantt-legend-color" style={{ background: l.color }} />
            {l.name}
          </span>
        ))}
      </div>

      <div className="gantt-chart">
        {/* Time axis */}
        <div className="gantt-row gantt-time-axis">
          <div className="gantt-label" />
          <div className="gantt-bars">
            {ticks.map((tick) => (
              <span
                key={tick.minutes}
                className="gantt-tick"
                style={{ left: `${((tick.minutes - totalStart) / totalDuration) * 100}%` }}
              >
                {tick.label}
              </span>
            ))}
          </div>
        </div>

        {/* Worker rows */}
        {workerRows.map((row) => (
          <div key={row.name} className="gantt-row">
            <div className="gantt-label" title={row.name}>{row.name}</div>
            <div className="gantt-bars">
              {row.segments.map((seg, i) => {
                const left = ((seg.startMinutes - totalStart) / totalDuration) * 100;
                const width = ((seg.endMinutes - seg.startMinutes) / totalDuration) * 100;
                return (
                  <div
                    key={i}
                    className="gantt-bar"
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      background: stationColorMap.get(seg.stationId) || "#999",
                    }}
                    title={`${seg.stationName}: ${formatMinutes(seg.startMinutes)} - ${formatMinutes(seg.endMinutes)}`}
                  >
                    <span className="gantt-bar-text">{seg.stationName}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
