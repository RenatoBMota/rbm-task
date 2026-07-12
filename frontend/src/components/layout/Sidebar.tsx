"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FolderOpen, CheckSquare, KanbanSquare, Calendar, BarChart3, Zap, LogOut, Tag, GanttChartSquare } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { WorkspaceSwitcher } from "@/components/workspace/WorkspaceSwitcher";
import { clsx } from "clsx";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/projects", label: "Projetos", icon: FolderOpen },
  { href: "/dashboard/tasks", label: "Tarefas", icon: CheckSquare },
  { href: "/dashboard/kanban", label: "Kanban", icon: KanbanSquare },
  { href: "/dashboard/gantt", label: "Gantt", icon: GanttChartSquare },
  { href: "/dashboard/calendar", label: "Calendário", icon: Calendar },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/labels", label: "Etiquetas", icon: Tag },
];

const adminNavItems = [
  { href: "/dashboard/automations", label: "Automações", icon: Zap },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const items = user?.role === "admin" ? [...navItems, ...adminNavItems] : navItems;

  return (
    <aside className="w-64 min-h-screen bg-surface-900 flex flex-col">
      <div className="px-6 py-5 border-b border-slate-700">
        <h1 className="text-white font-bold text-lg tracking-wide">RBM TASK</h1>
        <p className="text-slate-400 text-xs mt-0.5">Enterprise</p>
      </div>

      <WorkspaceSwitcher />

      <nav className="flex-1 px-3 py-4 space-y-1">
        {items.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              pathname === href
                ? "bg-primary-600 text-white"
                : "text-slate-400 hover:text-white hover:bg-slate-700"
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-semibold">
            {user?.full_name?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">{user?.full_name}</p>
            <p className="text-slate-400 text-xs truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-sm w-full px-2 py-1.5 rounded-lg hover:bg-slate-700 transition-colors"
        >
          <LogOut size={16} />
          Sair
        </button>
      </div>
    </aside>
  );
}
