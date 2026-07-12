"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileBottomNav } from "@/components/layout/MobileBottomNav";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { useAuthStore } from "@/store/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, fetchMe } = useAuthStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    if (!isAuthenticated) {
      fetchMe().catch(() => router.replace("/login"));
    }
  }, [isAuthenticated, fetchMe, router]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-100 dark:bg-surface-800 dark:bg-surface-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-surface-100 dark:bg-surface-800 dark:bg-surface-950">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="flex justify-between lg:justify-end items-center px-4 lg:px-8 py-2.5 lg:py-3 border-b border-surface-200 dark:border-slate-700 dark:border-slate-800 bg-white dark:bg-surface-900 sticky top-0 z-30">
          <span className="lg:hidden flex items-center gap-2 font-bold text-slate-900 dark:text-white text-sm tracking-wide">
            <img src="/logo-icon.png" alt="" className="w-6 h-6" /> TASK R PRO
          </span>
          <div className="flex items-center gap-3">
            <ThemeToggle className="hidden lg:flex" />
            <NotificationBell />
          </div>
        </header>
        <main className="flex-1 overflow-auto p-4 lg:p-8 pb-20 lg:pb-8">{children}</main>
      </div>
      <MobileBottomNav />
    </div>
  );
}
