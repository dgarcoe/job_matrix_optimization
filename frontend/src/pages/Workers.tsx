import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import type { Worker, Skill } from "../api/types";

export default function Workers() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [batchNames, setBatchNames] = useState("");
  const [batchMode, setBatchMode] = useState(false);
  const [selectedSkills, setSelectedSkills] = useState<number[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);

  const { data: workers, isLoading } = useQuery<Worker[]>({
    queryKey: ["workers"],
    queryFn: () => api.get("/api/workers").then((r) => r.data),
  });

  const { data: skills } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: () => api.get("/api/skills").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; skill_ids: number[] }) =>
      api.post("/api/workers", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workers"] });
      resetForm();
    },
  });

  const batchCreateMutation = useMutation({
    mutationFn: (data: { names: string[]; skill_ids: number[] }) =>
      api.post("/api/workers/batch", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workers"] });
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: { name: string; skill_ids: number[] };
    }) => api.put(`/api/workers/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workers"] });
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/workers/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workers"] }),
  });

  const resetForm = () => {
    setName("");
    setBatchNames("");
    setSelectedSkills([]);
    setEditingId(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingId !== null) {
      if (!name.trim()) return;
      updateMutation.mutate({ id: editingId, data: { name, skill_ids: selectedSkills } });
    } else if (batchMode) {
      const names = batchNames
        .split("\n")
        .map((n) => n.trim())
        .filter((n) => n.length > 0);
      if (names.length === 0) return;
      batchCreateMutation.mutate({ names, skill_ids: selectedSkills });
    } else {
      if (!name.trim()) return;
      createMutation.mutate({ name, skill_ids: selectedSkills });
    }
  };

  const startEdit = (worker: Worker) => {
    setBatchMode(false);
    setEditingId(worker.id);
    setName(worker.name);
    setSelectedSkills(worker.skills.map((s) => s.id));
  };

  const toggleSkill = (skillId: number) => {
    setSelectedSkills((prev) =>
      prev.includes(skillId)
        ? prev.filter((id) => id !== skillId)
        : [...prev, skillId]
    );
  };

  if (isLoading) return <p>{t("common.loading")}</p>;

  return (
    <div>
      <h2>{t("workers.title")}</h2>

      {editingId === null && (
        <div className="form-row" style={{ marginBottom: "0.5rem" }}>
          <button
            type="button"
            className={!batchMode ? "chip chip-active" : "chip"}
            onClick={() => { setBatchMode(false); resetForm(); }}
          >
            {t("workers.add")}
          </button>
          <button
            type="button"
            className={batchMode ? "chip chip-active" : "chip"}
            onClick={() => { setBatchMode(true); resetForm(); }}
          >
            {t("workers.add_batch")}
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="form-column">
        <div className="form-row">
          {batchMode && editingId === null ? (
            <textarea
              placeholder={t("workers.batch_placeholder")}
              value={batchNames}
              onChange={(e) => setBatchNames(e.target.value)}
              rows={4}
              required
              style={{ flex: 1 }}
            />
          ) : (
            <input
              type="text"
              placeholder={t("workers.name_placeholder")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          )}
          <button
            type="submit"
            disabled={batchCreateMutation.isPending || createMutation.isPending}
          >
            {editingId !== null ? t("common.save") : batchMode ? t("workers.add_batch") : t("workers.add")}
          </button>
          {editingId !== null && (
            <button type="button" onClick={resetForm}>
              {t("common.cancel")}
            </button>
          )}
        </div>
        {skills && skills.length > 0 && (
          <div className="skill-chips">
            <label>{t("workers.select_skills")}:</label>
            {skills.map((skill) => (
              <button
                key={skill.id}
                type="button"
                className={`chip ${selectedSkills.includes(skill.id) ? "chip-active" : ""}`}
                onClick={() => toggleSkill(skill.id)}
              >
                {skill.name}
              </button>
            ))}
          </div>
        )}
      </form>

      {workers && workers.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>{t("common.name")}</th>
              <th>{t("workers.skills")}</th>
              <th>{t("common.active")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {workers.map((worker) => (
              <tr key={worker.id}>
                <td>{worker.name}</td>
                <td>
                  {worker.skills.length > 0
                    ? worker.skills.map((s) => s.name).join(", ")
                    : t("workers.no_skills")}
                </td>
                <td>{worker.active ? "Yes" : "No"}</td>
                <td>
                  <button onClick={() => startEdit(worker)}>
                    {t("common.edit")}
                  </button>
                  <button
                    className="btn-danger"
                    onClick={() => {
                      if (confirm(t("common.confirm_delete"))) {
                        deleteMutation.mutate(worker.id);
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
    </div>
  );
}
