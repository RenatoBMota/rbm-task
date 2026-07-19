"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CheckSquare,
  KanbanSquare,
  Calendar,
  MoreHorizontal,
  X,
  FolderOpen,
  GanttChartSquare,
  Users2,
  BarChart3,
  FileBarChart,
  Tag,
  Zap,
  LogOut,
  Target,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";
import { useAuthStore } from "@/store/auth";
import { WorkspaceSwitcher } from "@/components/workspace/WorkspaceSwitcher";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const PRIMARY = [
  { href: "/dashboard", label: "Início", icon: LayoutDashboard },
  { href: "/dashboard/tasks", label: "Tarefas", icon: CheckSquare },
  { href: "/dashboard/kanban", label: "Kanban", icon: KanbanSquare },
  { href: "/dashboard/calendar", label: "Agenda", icon: Calendar },
];

const MORE_ITEMS = [
  { href: "/dashboard/okr", label: "OKRs", icon: Target },
  { href: "/dashboard/ai-tasks", label: "Tarefas por IA", icon: Sparkles },
  { href: "/dashboard/projects", label: "Projetos", icon: FolderOpen },
  { href: "/dashboard/gantt", label: "Gantt", icon: GanttChartSquare },
  { href: "/dashboard/resources", label: "Recursos", icon: Users2 },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/reports", label: "Relatórios", icon: FileBarChart },
  { href: "/dashboard/labels", label: "Etiquetas", icon: Tag },
];

const ADMIN_MORE_ITEMS = [{ href: "/dashboard/automations", label: "Automações", icon: Zap }];

export function MobileBottomNav() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [sheetOpen, setSheetOpen] = useState(false);
  const moreItems = user?.role === "admin" ? [...MORE_ITEMS, ...ADMIN_MORE_ITEMS] : MORE_ITEMS;
  const isMoreActive = moreItems.some((i) => pathname === i.href || pathname.startsWith(`${i.href}/`));

  return (
    <>
      <nav
        className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white dark:bg-surface-900 border-t border-surface-200 dark:border-slate-700 dark:border-slate-800 flex items-stretch"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {PRIMARY.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[52px] text-[11px] font-medium transition-colors",
                active ? "text-primary-600" : "text-slate-400 dark:text-slate-500"
              )}
            >
              <Icon size={20} />
              {label}
            </Link>
          );
        })}
        <button
          onClick={() => setSheetOpen(true)}
          className={clsx(
            "flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[52px] text-[11px] font-medium transition-colors",
            isMoreActive ? "text-primary-600" : "text-slate-400 dark:text-slate-500"
          )}
        >
          <MoreHorizontal size={20} />
          Mais
        </button>
      </nav>

      {sheetOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex items-end" onClick={() => setSheetOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div
            className="relative w-full bg-white dark:bg-surface-900 rounded-t-2xl max-h-[85vh] overflow-y-auto"
            style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-surface-100 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-white">Mais opções</span>
              <button onClick={() => setSheetOpen(false)} className="text-slate-400 p-1.5">
                <X size={18} />
              </button>
              <ThemeToggle />
            </div>

            <div className="p-3 rounded-xl m-3 bg-surface-950">
              <WorkspaceSwitcher />
            </div>

            <div className="px-3 pb-3 grid grid-cols-3 gap-2">
              {moreItems.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setSheetOpen(false)}
                  className={clsx(
                    "flex flex-col items-center justify-center gap-1.5 py-4 rounded-xl text-xs font-medium transition-colors",
                    pathname === href || pathname.startsWith(`${href}/`)
                      ? "bg-primary-50 text-primary-600 dark:bg-primary-600/10"
                      : "bg-surface-50 dark:bg-surface-800 text-slate-600 dark:text-slate-400 dark:text-slate-300"
                  )}
                >
                  <Icon size={20} />
                  {label}
                </Link>
              ))}
            </div>

            <div className="px-3 pb-4">
              <button
                onClick={logout}
                className="flex items-center justify-center gap-2 text-red-600 text-sm font-medium w-full px-3 py-3 rounded-xl bg-red-50 dark:bg-red-500/10"
              >
                <LogOut size={16} />
                Sair
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
