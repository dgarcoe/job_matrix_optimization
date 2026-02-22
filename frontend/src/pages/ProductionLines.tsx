import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";
import type { ProductionLine, Skill } from "../api/types";

export default function ProductionLines() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // Line form
  const [lineName, setLineName] = useState("");
  const [lineDesc, setLineDesc] = useState("");
  const [editingLineId, setEditingLineId] = useState<number | null>(null);

  // Station form
  const [expandedLine, setExpandedLine] = useState<number | null>(null);
  const [stationName, setStationName] = useState("");
  const [stationPosition, setStationPosition] = useState(1);
  const [workersNeeded, setWorkersNeeded] = useState(1);
  const [maxMinutes, setMaxMinutes] = useState(120);
  const [cycleTime, setCycleTime] = useState(1);
  const [requiredSkillIds, setRequiredSkillIds] = useState<number[]>([]);

  const { data: lines, isLoading } = useQuery<ProductionLine[]>({
    queryKey: ["lines"],
    queryFn: () => api.get("/api/production-lines").then((r) => r.data),
  });

  const { data: skills } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: () => api.get("/api/skills").then((r) => r.data),
  });

  const createLine = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      api.post("/api/production-lines", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lines"] });
      setLineName("");
      setLineDesc("");
    },
  });

  const updateLine = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: { name: string; description: string };
    }) => api.put(`/api/production-lines/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lines"] });
      setEditingLineId(null);
      setLineName("");
      setLineDesc("");
    },
  });

  const deleteLine = useMutation({
    mutationFn: (id: number) => api.delete(`/api/production-lines/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lines"] }),
  });

  const createStation = useMutation({
    mutationFn: ({
      lineId,
      data,
    }: {
      lineId: number;
      data: {
        name: string;
        production_line_id: number;
        position: number;
        workers_needed: number;
        max_minutes_per_worker: number;
        cycle_time_minutes: number;
        required_skill_ids: number[];
      };
    }) => api.post(`/api/production-lines/${lineId}/stations`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lines"] });
      resetStationForm();
    },
  });

  const deleteStation = useMutation({
    mutationFn: ({
      lineId,
      stationId,
    }: {
      lineId: number;
      stationId: number;
    }) =>
      api.delete(
        `/api/production-lines/${lineId}/stations/${stationId}`
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lines"] }),
  });

  const resetStationForm = () => {
    setStationName("");
    setStationPosition(1);
    setWorkersNeeded(1);
    setMaxMinutes(120);
    setCycleTime(1);
    setRequiredSkillIds([]);
  };

  const handleLineSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!lineName.trim()) return;
    const data = { name: lineName, description: lineDesc };
    if (editingLineId !== null) {
      updateLine.mutate({ id: editingLineId, data });
    } else {
      createLine.mutate(data);
    }
  };

  const handleStationSubmit = (e: React.FormEvent, lineId: number) => {
    e.preventDefault();
    if (!stationName.trim()) return;
    createStation.mutate({
      lineId,
      data: {
        name: stationName,
        production_line_id: lineId,
        position: stationPosition,
        workers_needed: workersNeeded,
        max_minutes_per_worker: maxMinutes,
        cycle_time_minutes: cycleTime,
        required_skill_ids: requiredSkillIds,
      },
    });
  };

  const toggleSkill = (skillId: number) => {
    setRequiredSkillIds((prev) =>
      prev.includes(skillId)
        ? prev.filter((id) => id !== skillId)
        : [...prev, skillId]
    );
  };

  if (isLoading) return <p>{t("common.loading")}</p>;

  return (
    <div>
      <h2>{t("lines.title")}</h2>

      <form onSubmit={handleLineSubmit} className="form-row">
        <input
          type="text"
          placeholder={t("lines.name_placeholder")}
          value={lineName}
          onChange={(e) => setLineName(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder={t("lines.desc_placeholder")}
          value={lineDesc}
          onChange={(e) => setLineDesc(e.target.value)}
        />
        <button type="submit">
          {editingLineId !== null ? t("common.save") : t("lines.add")}
        </button>
        {editingLineId !== null && (
          <button
            type="button"
            onClick={() => {
              setEditingLineId(null);
              setLineName("");
              setLineDesc("");
            }}
          >
            {t("common.cancel")}
          </button>
        )}
      </form>

      {lines && lines.length > 0 ? (
        <div className="lines-list">
          {lines.map((line) => (
            <div key={line.id} className="line-card">
              <div className="line-header">
                <div>
                  <strong>{line.name}</strong>
                  {line.description && (
                    <span className="line-desc"> - {line.description}</span>
                  )}
                  <span className="badge">
                    {line.stations.length} {t("lines.stations").toLowerCase()}
                  </span>
                </div>
                <div>
                  <button
                    onClick={() =>
                      setExpandedLine(
                        expandedLine === line.id ? null : line.id
                      )
                    }
                  >
                    {expandedLine === line.id
                      ? t("common.cancel")
                      : t("lines.stations")}
                  </button>
                  <button
                    onClick={() => {
                      setEditingLineId(line.id);
                      setLineName(line.name);
                      setLineDesc(line.description);
                    }}
                  >
                    {t("common.edit")}
                  </button>
                  <button
                    className="btn-danger"
                    onClick={() => {
                      if (confirm(t("common.confirm_delete"))) {
                        deleteLine.mutate(line.id);
                      }
                    }}
                  >
                    {t("common.delete")}
                  </button>
                </div>
              </div>

              {expandedLine === line.id && (
                <div className="stations-section">
                  <h4>{t("lines.add_station")}</h4>
                  <form
                    onSubmit={(e) => handleStationSubmit(e, line.id)}
                    className="form-column"
                  >
                    <div className="form-row">
                      <input
                        type="text"
                        placeholder={t("lines.station_name")}
                        value={stationName}
                        onChange={(e) => setStationName(e.target.value)}
                        required
                      />
                      <label>
                        {t("lines.position")}
                        <input
                          type="number"
                          min={1}
                          value={stationPosition}
                          onChange={(e) =>
                            setStationPosition(Number(e.target.value))
                          }
                        />
                      </label>
                      <label>
                        {t("lines.workers_needed")}
                        <input
                          type="number"
                          min={1}
                          value={workersNeeded}
                          onChange={(e) =>
                            setWorkersNeeded(Number(e.target.value))
                          }
                        />
                      </label>
                    </div>
                    <div className="form-row">
                      <label>
                        {t("lines.max_minutes")}
                        <input
                          type="number"
                          min={1}
                          value={maxMinutes}
                          onChange={(e) =>
                            setMaxMinutes(Number(e.target.value))
                          }
                        />
                      </label>
                      <label>
                        {t("lines.cycle_time")}
                        <input
                          type="number"
                          min={0.1}
                          step={0.1}
                          value={cycleTime}
                          onChange={(e) =>
                            setCycleTime(Number(e.target.value))
                          }
                        />
                      </label>
                    </div>
                    {skills && skills.length > 0 && (
                      <div className="skill-chips">
                        <label>{t("lines.required_skills")}:</label>
                        {skills.map((skill) => (
                          <button
                            key={skill.id}
                            type="button"
                            className={`chip ${requiredSkillIds.includes(skill.id) ? "chip-active" : ""}`}
                            onClick={() => toggleSkill(skill.id)}
                          >
                            {skill.name}
                          </button>
                        ))}
                      </div>
                    )}
                    <button type="submit">{t("lines.add_station")}</button>
                  </form>

                  {line.stations.length > 0 && (
                    <table>
                      <thead>
                        <tr>
                          <th>{t("lines.position")}</th>
                          <th>{t("common.name")}</th>
                          <th>{t("lines.workers_needed")}</th>
                          <th>{t("lines.max_minutes")}</th>
                          <th>{t("lines.cycle_time")}</th>
                          <th>{t("lines.required_skills")}</th>
                          <th>{t("common.actions")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...line.stations]
                          .sort((a, b) => a.position - b.position)
                          .map((station) => (
                            <tr key={station.id}>
                              <td>{station.position}</td>
                              <td>{station.name}</td>
                              <td>{station.workers_needed}</td>
                              <td>{station.max_minutes_per_worker}</td>
                              <td>{station.cycle_time_minutes}</td>
                              <td>
                                {station.required_skills
                                  .map((s) => s.name)
                                  .join(", ") || "-"}
                              </td>
                              <td>
                                <button
                                  className="btn-danger"
                                  onClick={() => {
                                    if (confirm(t("common.confirm_delete"))) {
                                      deleteStation.mutate({
                                        lineId: line.id,
                                        stationId: station.id,
                                      });
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
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p>{t("common.no_data")}</p>
      )}
    </div>
  );
}
