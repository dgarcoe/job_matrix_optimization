import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import api from "../api/client";
import type { Worker, Skill, Shift, ProductionLine } from "../api/types";

export default function Dashboard() {
  const { t } = useTranslation();

  const { data: workers } = useQuery<Worker[]>({
    queryKey: ["workers"],
    queryFn: () => api.get("/api/workers").then((r) => r.data),
  });
  const { data: skills } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: () => api.get("/api/skills").then((r) => r.data),
  });
  const { data: shifts } = useQuery<Shift[]>({
    queryKey: ["shifts"],
    queryFn: () => api.get("/api/shifts").then((r) => r.data),
  });
  const { data: lines } = useQuery<ProductionLine[]>({
    queryKey: ["lines"],
    queryFn: () => api.get("/api/production-lines").then((r) => r.data),
  });

  const stats = [
    { label: t("app.nav.workers"), value: workers?.length ?? 0 },
    { label: t("app.nav.skills"), value: skills?.length ?? 0 },
    { label: t("app.nav.shifts"), value: shifts?.length ?? 0 },
    { label: t("app.nav.lines"), value: lines?.length ?? 0 },
    {
      label: t("optimize.station"),
      value: lines?.reduce((acc, l) => acc + l.stations.length, 0) ?? 0,
    },
  ];

  return (
    <div>
      <h2>{t("app.nav.dashboard")}</h2>
      <div className="stats-grid">
        {stats.map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
