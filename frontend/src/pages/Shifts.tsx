import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import type { Shift, ShiftAssignment, Worker } from "../api/types";

function formatHour(h: number): string {
  const hours = Math.floor(h);
  const mins = Math.round((h - hours) * 60);
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

function WorkerChecklist({
  shift,
  workers,
  assignments,
}: {
  shift: Shift;
  workers: Worker[];
  assignments: ShiftAssignment[];
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const assignedIds = new Set(
    assignments.filter((a) => a.shift_id === shift.id).map((a) => a.worker_id)
  );
  const [selected, setSelected] = useState<Set<number>>(new Set(assignedIds));
  const [saved, setSaved] = useState(false);

  const batchMutation = useMutation({
    mutationFn: (workerIds: number[]) =>
      api.put(`/api/shifts/${shift.id}/assignments/batch`, {
        worker_ids: workerIds,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shift-assignments"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const toggle = (workerId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(workerId)) next.delete(workerId);
      else next.add(workerId);
      return next;
    });
    setSaved(false);
  };

  const selectAll = () => {
    setSelected(new Set(workers.map((w) => w.id)));
    setSaved(false);
  };

  const selectNone = () => {
    setSelected(new Set());
    setSaved(false);
  };

  const hasChanges =
    selected.size !== assignedIds.size ||
    [...selected].some((id) => !assignedIds.has(id));

  return (
    <div className="worker-checklist">
      <div className="checklist-toolbar">
        <button type="button" className="btn-sm" onClick={selectAll}>
          {t("shifts.select_all")}
        </button>
        <button type="button" className="btn-sm" onClick={selectNone}>
          {t("shifts.select_none")}
        </button>
        <span className="checklist-count">
          {selected.size} / {workers.length} {t("shifts.selected")}
        </span>
      </div>

      <div className="checklist-grid">
        {workers.map((w) => (
          <label key={w.id} className={`checklist-item ${selected.has(w.id) ? "checklist-item-checked" : ""}`}>
            <input
              type="checkbox"
              checked={selected.has(w.id)}
              onChange={() => toggle(w.id)}
            />
            <span className="checklist-name">{w.name}</span>
            {w.skills.length > 0 && (
              <span className="checklist-skills">
                {w.skills.map((s) => s.name).join(", ")}
              </span>
            )}
          </label>
        ))}
      </div>

      <div className="checklist-actions">
        <button
          type="button"
          disabled={!hasChanges || batchMutation.isPending}
          onClick={() => batchMutation.mutate([...selected])}
        >
          {batchMutation.isPending ? t("common.loading") : t("shifts.apply")}
        </button>
        {saved && <span className="checklist-saved">{t("shifts.saved")}</span>}
        {batchMutation.isError && (
          <span className="checklist-error">{t("common.error")}</span>
        )}
      </div>
    </div>
  );
}

export default function Shifts() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // Shift form
  const [name, setName] = useState("");
  const [startHour, setStartHour] = useState(6);
  const [endHour, setEndHour] = useState(14);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [expandedShiftId, setExpandedShiftId] = useState<number | null>(null);

  const { data: shifts, isLoading } = useQuery<Shift[]>({
    queryKey: ["shifts"],
    queryFn: () => api.get("/api/shifts").then((r) => r.data),
  });

  const { data: workers } = useQuery<Worker[]>({
    queryKey: ["workers"],
    queryFn: () => api.get("/api/workers").then((r) => r.data),
  });

  const { data: assignments } = useQuery<ShiftAssignment[]>({
    queryKey: ["shift-assignments"],
    queryFn: () => api.get("/api/shifts/assignments/all").then((r) => r.data),
  });

  const createShift = useMutation({
    mutationFn: (data: {
      name: string;
      start_hour: number;
      end_hour: number;
    }) => api.post("/api/shifts", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shifts"] });
      resetForm();
    },
  });

  const updateShift = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: { name: string; start_hour: number; end_hour: number };
    }) => api.put(`/api/shifts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shifts"] });
      resetForm();
    },
  });

  const deleteShift = useMutation({
    mutationFn: (id: number) => api.delete(`/api/shifts/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shifts"] }),
  });

  const resetForm = () => {
    setName("");
    setStartHour(6);
    setEndHour(14);
    setEditingId(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const data = { name, start_hour: startHour, end_hour: endHour };
    if (editingId !== null) {
      updateShift.mutate({ id: editingId, data });
    } else {
      createShift.mutate(data);
    }
  };

  const startEdit = (shift: Shift) => {
    setEditingId(shift.id);
    setName(shift.name);
    setStartHour(shift.start_hour);
    setEndHour(shift.end_hour);
  };

  if (isLoading) return <p>{t("common.loading")}</p>;

  return (
    <div>
      <h2>{t("shifts.title")}</h2>

      <form onSubmit={handleSubmit} className="form-row">
        <input
          type="text"
          placeholder={t("shifts.name_placeholder")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <label>
          {t("shifts.start_hour")}
          <input
            type="number"
            min={0}
            max={23.5}
            step={0.5}
            value={startHour}
            onChange={(e) => setStartHour(Number(e.target.value))}
          />
        </label>
        <label>
          {t("shifts.end_hour")}
          <input
            type="number"
            min={0.5}
            max={24}
            step={0.5}
            value={endHour}
            onChange={(e) => setEndHour(Number(e.target.value))}
          />
        </label>
        <button type="submit">
          {editingId !== null ? t("common.save") : t("shifts.add")}
        </button>
        {editingId !== null && (
          <button type="button" onClick={resetForm}>
            {t("common.cancel")}
          </button>
        )}
      </form>

      {shifts && shifts.length > 0 ? (
        <div className="lines-list">
          {shifts.map((shift) => {
            const shiftAssignmentCount = assignments
              ? assignments.filter((a) => a.shift_id === shift.id).length
              : 0;
            const isExpanded = expandedShiftId === shift.id;
            return (
              <div key={shift.id} className="line-card">
                <div className="line-header">
                  <div>
                    <strong>{shift.name}</strong>
                    <span className="line-desc">
                      {" "}
                      {formatHour(shift.start_hour)} –{" "}
                      {formatHour(shift.end_hour)}
                    </span>
                    <span className="badge">
                      {shiftAssignmentCount} {t("shifts.workers_assigned")}
                    </span>
                  </div>
                  <div>
                    <button
                      onClick={() =>
                        setExpandedShiftId(isExpanded ? null : shift.id)
                      }
                    >
                      {isExpanded
                        ? t("common.cancel")
                        : t("shifts.manage_workers")}
                    </button>
                    <button onClick={() => startEdit(shift)}>
                      {t("common.edit")}
                    </button>
                    <button
                      className="btn-danger"
                      onClick={() => {
                        if (confirm(t("common.confirm_delete"))) {
                          deleteShift.mutate(shift.id);
                        }
                      }}
                    >
                      {t("common.delete")}
                    </button>
                  </div>
                </div>

                {isExpanded && workers && assignments && (
                  <div className="stations-section">
                    <WorkerChecklist
                      shift={shift}
                      workers={workers.filter((w) => w.active)}
                      assignments={assignments}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p>{t("common.no_data")}</p>
      )}
    </div>
  );
}
