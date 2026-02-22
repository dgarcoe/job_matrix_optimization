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

export default function Shifts() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // Shift form
  const [name, setName] = useState("");
  const [startHour, setStartHour] = useState(6);
  const [endHour, setEndHour] = useState(14);
  const [editingId, setEditingId] = useState<number | null>(null);

  // Assignment form
  const [assignWorkerId, setAssignWorkerId] = useState<number | "">("");
  const [assignShiftId, setAssignShiftId] = useState<number | "">("");

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

  const createAssignment = useMutation({
    mutationFn: (data: { worker_id: number; shift_id: number }) =>
      api.post("/api/shifts/assignments", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shift-assignments"] });
      setAssignWorkerId("");
      setAssignShiftId("");
    },
  });

  const deleteAssignment = useMutation({
    mutationFn: (id: number) =>
      api.delete(`/api/shifts/assignments/${id}`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["shift-assignments"] }),
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

  const handleAssign = (e: React.FormEvent) => {
    e.preventDefault();
    if (assignWorkerId === "" || assignShiftId === "") return;
    createAssignment.mutate({
      worker_id: assignWorkerId as number,
      shift_id: assignShiftId as number,
    });
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
        <table>
          <thead>
            <tr>
              <th>{t("common.name")}</th>
              <th>{t("shifts.start_hour")}</th>
              <th>{t("shifts.end_hour")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {shifts.map((shift) => (
              <tr key={shift.id}>
                <td>{shift.name}</td>
                <td>{formatHour(shift.start_hour)}</td>
                <td>{formatHour(shift.end_hour)}</td>
                <td>
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
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>{t("common.no_data")}</p>
      )}

      <h3>{t("shifts.assignments")}</h3>
      <form onSubmit={handleAssign} className="form-row">
        <select
          value={assignWorkerId}
          onChange={(e) =>
            setAssignWorkerId(e.target.value ? Number(e.target.value) : "")
          }
          required
        >
          <option value="">{t("shifts.select_worker")}</option>
          {workers?.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <select
          value={assignShiftId}
          onChange={(e) =>
            setAssignShiftId(e.target.value ? Number(e.target.value) : "")
          }
          required
        >
          <option value="">{t("shifts.select_shift")}</option>
          {shifts?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <button type="submit">{t("shifts.assign_worker")}</button>
      </form>

      {assignments && assignments.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>{t("app.nav.workers")}</th>
              <th>{t("app.nav.shifts")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={a.id}>
                <td>{a.worker.name}</td>
                <td>{a.shift.name}</td>
                <td>
                  <button
                    className="btn-danger"
                    onClick={() => deleteAssignment.mutate(a.id)}
                  >
                    {t("common.delete")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>{t("common.no_data")}</p>
      )}
    </div>
  );
}
