import { useState, useCallback, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ReactFlow,
  Controls,
  Background,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Connection,
  type Edge,
  type Node,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import api from "../api/client";
import type { ProductionLine, Skill, Station } from "../api/types";
import StationNode from "../components/StationNode";

const nodeTypes = { station: StationNode };

export default function FlowEditor() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selectedLineId, setSelectedLineId] = useState<number | "">("");
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Station dialog state
  const [showDialog, setShowDialog] = useState(false);
  const [editingStationId, setEditingStationId] = useState<number | null>(null);
  const [stationName, setStationName] = useState("");
  const [workersNeeded, setWorkersNeeded] = useState(1);
  const [maxMinutes, setMaxMinutes] = useState(120);
  const [cycleTime, setCycleTime] = useState(1);
  const [requiredSkillIds, setRequiredSkillIds] = useState<number[]>([]);

  const { data: lines } = useQuery<ProductionLine[]>({
    queryKey: ["lines"],
    queryFn: () => api.get("/api/production-lines").then((r) => r.data),
  });

  const { data: skills } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: () => api.get("/api/skills").then((r) => r.data),
  });

  const selectedLine = useMemo(
    () => lines?.find((l) => l.id === selectedLineId) ?? null,
    [lines, selectedLineId]
  );

  // Sync nodes/edges when line data changes
  useEffect(() => {
    if (!selectedLine) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const newNodes: Node[] = selectedLine.stations.map(
      (station: Station, idx: number) => ({
        id: String(station.id),
        type: "station",
        position: {
          x: station.layout_x || idx * 250,
          y: station.layout_y || 100,
        },
        data: {
          label: station.name,
          workersNeeded: station.workers_needed,
          maxMinutes: station.max_minutes_per_worker,
          cycleTime: station.cycle_time_minutes,
          skills: station.required_skills.map((s) => s.name),
          active: station.active,
          onEdit: handleEditStation,
          onDelete: handleDeleteStation,
        },
      })
    );

    const newEdges: Edge[] = (selectedLine.connections || []).map((conn) => ({
      id: `conn-${conn.id}`,
      source: String(conn.source_station_id),
      target: String(conn.target_station_id),
      label: conn.label || undefined,
      markerEnd: { type: MarkerType.ArrowClosed },
      animated: true,
      data: { connectionId: conn.id },
    }));

    setNodes(newNodes);
    setEdges(newEdges);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLine]);

  // --- Mutations ---
  const createStation = useMutation({
    mutationFn: (data: {
      name: string;
      production_line_id: number;
      position: number;
      workers_needed: number;
      max_minutes_per_worker: number;
      cycle_time_minutes: number;
      required_skill_ids: number[];
      layout_x: number;
      layout_y: number;
    }) =>
      api.post(`/api/production-lines/${data.production_line_id}/stations`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lines"] });
      closeDialog();
    },
  });

  const updateStation = useMutation({
    mutationFn: ({
      lineId,
      stationId,
      data,
    }: {
      lineId: number;
      stationId: number;
      data: Record<string, unknown>;
    }) => api.put(`/api/production-lines/${lineId}/stations/${stationId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lines"] });
      closeDialog();
    },
  });

  const deleteStationMut = useMutation({
    mutationFn: ({
      lineId,
      stationId,
    }: {
      lineId: number;
      stationId: number;
    }) =>
      api.delete(`/api/production-lines/${lineId}/stations/${stationId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lines"] }),
  });

  const createConnection = useMutation({
    mutationFn: ({
      lineId,
      data,
    }: {
      lineId: number;
      data: {
        source_station_id: number;
        target_station_id: number;
        label: string;
      };
    }) => api.post(`/api/production-lines/${lineId}/connections`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lines"] }),
  });

  const deleteConnection = useMutation({
    mutationFn: ({
      lineId,
      connectionId,
    }: {
      lineId: number;
      connectionId: number;
    }) =>
      api.delete(`/api/production-lines/${lineId}/connections/${connectionId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lines"] }),
  });

  // --- Handlers ---
  const handleEditStation = useCallback(
    (nodeId: string) => {
      if (!selectedLine) return;
      const station = selectedLine.stations.find(
        (s) => s.id === Number(nodeId)
      );
      if (!station) return;
      setEditingStationId(station.id);
      setStationName(station.name);
      setWorkersNeeded(station.workers_needed);
      setMaxMinutes(station.max_minutes_per_worker);
      setCycleTime(station.cycle_time_minutes);
      setRequiredSkillIds(station.required_skills.map((s) => s.id));
      setShowDialog(true);
    },
    [selectedLine]
  );

  const handleDeleteStation = useCallback(
    (nodeId: string) => {
      if (!selectedLine) return;
      if (!confirm(t("common.confirm_delete"))) return;
      deleteStationMut.mutate({
        lineId: selectedLine.id,
        stationId: Number(nodeId),
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedLine, t]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!selectedLine || !connection.source || !connection.target) return;
      createConnection.mutate({
        lineId: selectedLine.id,
        data: {
          source_station_id: Number(connection.source),
          target_station_id: Number(connection.target),
          label: "",
        },
      });
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            markerEnd: { type: MarkerType.ArrowClosed },
            animated: true,
          },
          eds
        )
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedLine]
  );

  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      if (!selectedLine) return;
      for (const edge of deletedEdges) {
        const connId = edge.data?.connectionId;
        if (connId) {
          deleteConnection.mutate({
            lineId: selectedLine.id,
            connectionId: connId as number,
          });
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedLine]
  );

  const onNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (!selectedLine) return;
      updateStation.mutate({
        lineId: selectedLine.id,
        stationId: Number(node.id),
        data: {
          layout_x: node.position.x,
          layout_y: node.position.y,
        },
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedLine]
  );

  const closeDialog = () => {
    setShowDialog(false);
    setEditingStationId(null);
    setStationName("");
    setWorkersNeeded(1);
    setMaxMinutes(120);
    setCycleTime(1);
    setRequiredSkillIds([]);
  };

  const handleStationSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLine || !stationName.trim()) return;

    if (editingStationId !== null) {
      updateStation.mutate({
        lineId: selectedLine.id,
        stationId: editingStationId,
        data: {
          name: stationName,
          workers_needed: workersNeeded,
          max_minutes_per_worker: maxMinutes,
          cycle_time_minutes: cycleTime,
          required_skill_ids: requiredSkillIds,
        },
      });
    } else {
      const nextPos = selectedLine.stations.length + 1;
      // Place new nodes in a grid-like layout
      const x = (nextPos - 1) * 250;
      const y = 100;
      createStation.mutate({
        name: stationName,
        production_line_id: selectedLine.id,
        position: nextPos,
        workers_needed: workersNeeded,
        max_minutes_per_worker: maxMinutes,
        cycle_time_minutes: cycleTime,
        required_skill_ids: requiredSkillIds,
        layout_x: x,
        layout_y: y,
      });
    }
  };

  const toggleSkill = (skillId: number) => {
    setRequiredSkillIds((prev) =>
      prev.includes(skillId)
        ? prev.filter((id) => id !== skillId)
        : [...prev, skillId]
    );
  };

  return (
    <div className="flow-editor-page">
      <div className="flow-editor-toolbar">
        <h2>{t("flow.title")}</h2>
        <div className="flow-editor-controls">
          <select
            value={selectedLineId}
            onChange={(e) =>
              setSelectedLineId(
                e.target.value ? Number(e.target.value) : ""
              )
            }
          >
            <option value="">{t("optimize.select_line")}</option>
            {lines?.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          {selectedLine && (
            <button onClick={() => setShowDialog(true)}>
              {t("flow.add_station")}
            </button>
          )}
        </div>
      </div>

      {selectedLine ? (
        <div className="flow-editor-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onEdgesDelete={onEdgesDelete}
            onNodeDragStop={onNodeDragStop}
            nodeTypes={nodeTypes}
            fitView
            deleteKeyCode="Delete"
          >
            <Controls />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>
      ) : (
        <div className="flow-editor-empty">
          <p>{t("flow.select_line_hint")}</p>
        </div>
      )}

      {/* Station Dialog */}
      {showDialog && (
        <div className="dialog-overlay" onClick={closeDialog}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>
              {editingStationId !== null
                ? t("flow.edit_station")
                : t("flow.add_station")}
            </h3>
            <form onSubmit={handleStationSubmit} className="form-column">
              <label>
                {t("common.name")}
                <input
                  type="text"
                  value={stationName}
                  onChange={(e) => setStationName(e.target.value)}
                  required
                  autoFocus
                />
              </label>
              <div className="form-row">
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
              <div className="dialog-buttons">
                <button type="submit">
                  {editingStationId !== null
                    ? t("common.save")
                    : t("flow.add_station")}
                </button>
                <button type="button" onClick={closeDialog}>
                  {t("common.cancel")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
