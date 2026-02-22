import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import type { Skill } from "../api/types";

export default function Skills() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);

  const { data: skills, isLoading } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: () => api.get("/api/skills").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      api.post("/api/skills", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] });
      setName("");
      setDescription("");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: { name: string; description: string };
    }) => api.put(`/api/skills/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] });
      setEditingId(null);
      setName("");
      setDescription("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/skills/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["skills"] }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, data: { name, description } });
    } else {
      createMutation.mutate({ name, description });
    }
  };

  const startEdit = (skill: Skill) => {
    setEditingId(skill.id);
    setName(skill.name);
    setDescription(skill.description);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setName("");
    setDescription("");
  };

  if (isLoading) return <p>{t("common.loading")}</p>;

  return (
    <div>
      <h2>{t("skills.title")}</h2>

      <form onSubmit={handleSubmit} className="form-row">
        <input
          type="text"
          placeholder={t("skills.name_placeholder")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder={t("skills.desc_placeholder")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button type="submit">
          {editingId !== null ? t("common.save") : t("skills.add")}
        </button>
        {editingId !== null && (
          <button type="button" onClick={cancelEdit}>
            {t("common.cancel")}
          </button>
        )}
      </form>

      {skills && skills.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>{t("common.name")}</th>
              <th>{t("common.description")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((skill) => (
              <tr key={skill.id}>
                <td>{skill.name}</td>
                <td>{skill.description}</td>
                <td>
                  <button onClick={() => startEdit(skill)}>
                    {t("common.edit")}
                  </button>
                  <button
                    className="btn-danger"
                    onClick={() => {
                      if (confirm(t("common.confirm_delete"))) {
                        deleteMutation.mutate(skill.id);
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
