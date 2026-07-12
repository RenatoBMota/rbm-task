"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { FileSpreadsheet, FileText } from "lucide-react";
import api from "@/lib/api";
import type { Project } from "@/lib/types";

interface TrendPoint {
  date: string;
  completed: number;
}

interface StatusItem {
  status: string;
  count: number;
}

interface SLACompliance {
  total: number;
  on_time: number;
  breached: number;
  at_risk: number;
  compliance_pct: number;
}

const STATUS_LABELS: Record<string, string> = {
  todo: "A Fazer",
  in_progress: "Em Progresso",
  in_review: "Em Revisão",
  done: "Concluído",
  cancelled: "Cancelado",
};

export default function AnalyticsPage() {
  const [projectId, setProjectId] = useState<number | "">("");

  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: () => api.get("/projects/").then((r) => r.data),
  });

  const params = projectId ? { project_id: projectId } : {};

  const { data: trend = [] } = useQuery<TrendPoint[]>({
    queryKey: ["analytics", "completion-trend", projectId],
    queryFn: () => api.get("/analytics/completion-trend", { params: { ...params, days: 30 } }).then((r) => r.data),
  });

  const { data: statusBreakdown = [] } = useQuery<StatusItem[]>({
    queryKey: ["analytics", "status-breakdown", projectId],
    queryFn: () => api.get("/analytics/status-breakdown", { params }).then((r) => r.data),
  });

  const { data: sla } = useQuery<SLACompliance>({
    queryKey: ["analytics", "sla-compliance", projectId],
    queryFn: () => api.get("/analytics/sla-compliance", { params }).then((r) => r.data),
  });

  const downloadReport = async (format: "xlsx" | "pdf") => {
    const response = await api.get(`/reports/tasks.${format}`, { params, responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `tarefas.${format}`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const statusData = statusBreakdown.map((s) => ({
    status: STATUS_LABELS[s.status] ?? s.status,
    count: s.count,
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
        <div className="flex items-center gap-3">
          <select
            className="input w-56"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Todos os projetos</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button className="btn-secondary flex items-center gap-2" onClick={() => downloadReport("xlsx")}>
            <FileSpreadsheet size={16} /> Excel
          </button>
          <button className="btn-secondary flex items-center gap-2" onClick={() => downloadReport("pdf")}>
            <FileText size={16} /> PDF
          </button>
        </div>
      </div>

      {sla && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <StatTile label="Total de tarefas" value={sla.total} />
          <StatTile label="Dentro do prazo" value={sla.on_time} tone="good" />
          <StatTile label="Em risco" value={sla.at_risk} tone="warning" />
          <StatTile label="Prazo estourado" value={sla.breached} tone="critical" />
        </div>
      )}

      {sla && (
        <div className="card p-5 mb-8">
          <p className="text-sm text-slate-500 mb-2">Cumprimento de SLA</p>
          <div className="flex items-center gap-4">
            <span className="text-3xl font-bold text-slate-900">{sla.compliance_pct}%</span>
            <div className="flex-1 h-2 bg-surface-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 rounded-full"
                style={{ width: `${sla.compliance_pct}%` }}
              />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="font-semibold text-slate-900 mb-4">Tarefas concluídas (últimos 30 dias)</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => v.slice(5)}
                interval={Math.max(Math.floor(trend.length / 8), 0)}
              />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={30} />
              <Tooltip />
              <Bar dataKey="completed" name="Concluídas" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h2 className="font-semibold text-slate-900 mb-4">Tarefas por status</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={statusData} layout="vertical" margin={{ left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="status" tick={{ fontSize: 12 }} width={110} />
              <Tooltip />
              <Bar dataKey="count" name="Tarefas" fill="#4f46e5" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "good" | "warning" | "critical";
}) {
  const toneClasses: Record<string, string> = {
    good: "text-green-600 bg-green-50",
    warning: "text-amber-600 bg-amber-50",
    critical: "text-red-600 bg-red-50",
  };
  return (
    <div className="card p-5">
      <p className={`text-2xl font-bold ${tone ? toneClasses[tone].split(" ")[0] : "text-slate-900"}`}>
        {value}
      </p>
      <p className="text-sm text-slate-500 mt-0.5">{label}</p>
    </div>
  );
}
