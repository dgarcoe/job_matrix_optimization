import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

export interface StationNodeData {
  label: string;
  workersNeeded: number;
  maxMinutes: number;
  cycleTime: number;
  skills: string[];
  active: boolean;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  [key: string]: unknown;
}

function StationNode({ id, data }: NodeProps) {
  const d = data as StationNodeData;
  return (
    <div className={`station-node ${d.active ? "" : "station-inactive"}`}>
      <Handle type="target" position={Position.Left} />
      <div className="station-node-header">
        <strong>{d.label}</strong>
        <div className="station-node-actions">
          <button
            className="node-btn"
            onClick={(e) => {
              e.stopPropagation();
              d.onEdit(id);
            }}
            title="Edit"
          >
            &#9998;
          </button>
          <button
            className="node-btn node-btn-danger"
            onClick={(e) => {
              e.stopPropagation();
              d.onDelete(id);
            }}
            title="Delete"
          >
            &times;
          </button>
        </div>
      </div>
      <div className="station-node-body">
        <div className="station-node-stat">
          <span className="stat-icon">&#128100;</span> {d.workersNeeded}
        </div>
        <div className="station-node-stat">
          <span className="stat-icon">&#9201;</span> {d.maxMinutes}m
        </div>
        <div className="station-node-stat">
          <span className="stat-icon">&#9881;</span> {d.cycleTime}m
        </div>
      </div>
      {d.skills.length > 0 && (
        <div className="station-node-skills">
          {d.skills.map((s) => (
            <span key={s} className="node-skill-chip">
              {s}
            </span>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export default memo(StationNode);
