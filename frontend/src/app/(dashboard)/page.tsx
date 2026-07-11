"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, AlertCircle, FolderOpen } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/auth";

interface Task {
  id: number;
  title: string;
  priority: string;
  status: string;
  due_date: string | null;
  is_completed: boolean;
}

interface Project {
  id: number;
  name: string;
  color: string;
}

const priorityColors: Record<string, string> = {
  P1: "bg-red-100 text-red-700",
  P2: "bg-orange-100 text-orange-700",
  P3: "bg-blue-100 text-blue-700",
  P4: "bg-slate-100 text-slate-600",
};

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  const { data: todayTasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks", "today"],
    queryFn: () => api.get("/tasks/today").then((r) => r.data),
  });

  const { data: overdueTasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks", "overdue"],
    queryFn: () => api.get("/tasks/overdue").then((r) => r.data),
  });

  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: () => api.get("/projects/").then((r) => r.data),
  });

  const { data: allTasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: () => api.get("/tasks/").then((r) => r.data),
  });

  const completedToday = allTasks.filter((t) => t.is_completed).length;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Bom dia, {user?.full_name?.split(" ")[0]} 👋
        </h1>
        <p className="text-slate-500 mt-1">Aqui está o resumo do seu dia</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Clock size={20} />} label="Para hoje" value={todayTasks.length} color="blue" />
        <StatCard icon={<AlertCircle size={20} />} label="Atrasadas" value={overdueTasks.length} color="red" />
        <StatCard icon={<CheckCircle2 size={20} />} label="Concluídas" value={completedToday} color="green" />
        <StatCard icon={<FolderOpen size={20} />} label="Projetos ativos" value={projects.length} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TaskList title="Tarefas de Hoje" tasks={todayTasks} emptyMsg="Nenhuma tarefa para hoje" />
        <TaskList title="Tarefas Atrasadas" tasks={overdueTasks} emptyMsg="Nenhuma tarefa atrasada" urgent />
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  const colors: Record<string, string> = {
    blue: "text-blue-600 bg-blue-50",
    red: "text-red-600 bg-red-50",
    green: "text-green-600 bg-green-50",
    purple: "text-purple-600 bg-purple-50",
  };

  return (
    <div className="card p-5">
      <div className={`inline-flex p-2 rounded-lg ${colors[color]} mb-3`}>{icon}</div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-sm text-slate-500 mt-0.5">{label}</p>
    </div>
  );
}

function TaskList({
  title,
  tasks,
  emptyMsg,
  urgent,
}: {
  title: string;
  tasks: { id: number; title: string; priority: string }[];
  emptyMsg: string;
  urgent?: boolean;
}) {
  return (
    <div className="card p-6">
      <h2 className={`font-semibold mb-4 ${urgent ? "text-red-700" : "text-slate-900"}`}>{title}</h2>
      {tasks.length === 0 ? (
        <p className="text-slate-400 text-sm">{emptyMsg}</p>
      ) : (
        <ul className="space-y-2">
          {tasks.map((t) => (
            <li key={t.id} className="flex items-center gap-3 py-2 border-b border-surface-100 last:border-0">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${priorityColors[t.priority]}`}>
                {t.priority}
              </span>
              <span className="text-sm text-slate-700 flex-1 truncate">{t.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
