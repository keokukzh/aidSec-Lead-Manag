"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Target,
  TrendingUp,
  Mail,
  Lightbulb,
  Settings,
  Upload,
  LogOut,
  Shield,
  Kanban,
  Inbox,
  BarChart2,
  Server,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth-store";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { rankingApi } from "@/lib/api";
import { useState, useEffect } from "react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Leads", href: "/leads", icon: Users },
  { name: "Pipeline", href: "/leads/pipeline", icon: Kanban },
  { name: "Kampagnen", href: "/kampagnen", icon: Target },
  { name: "AI Drafts", href: "/drafts", icon: Inbox },
  { name: "Conversion Health", href: "/analytics", icon: BarChart2 },
  {
    name: "Agent Queue",
    href: "/tasks",
    icon: Server,
  },
  { name: "Import", href: "/import", icon: Upload },
  { name: "Ranking", href: "/ranking", icon: TrendingUp },
  { name: "E-Mail", href: "/email", icon: Mail },
  { name: "Marketing Ideen", href: "/marketing", icon: Lightbulb },
  { name: "Einstellungen", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuthStore();

  const [rankingJobId, setRankingJobId] = useState<string | null>(null);

  // Poll local storage to see if a background job was started
  useEffect(() => {
    if (typeof window === "undefined") return;
    const interval = setInterval(() => {
       const jobId = localStorage.getItem("aidsec_ranking_job");
       setRankingJobId(jobId);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const queryClient = useQueryClient();

  const { data: jobStatus } = useQuery({
    queryKey: ["ranking-job-sidebar", rankingJobId],
    queryFn: () => rankingJobId ? rankingApi.getBatchStatus(rankingJobId) : null,
    enabled: !!rankingJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "failed") {
        localStorage.removeItem("aidsec_ranking_job");
        setRankingJobId(null);
        if (status === "done") {
          queryClient.invalidateQueries({ queryKey: ["ranking"] });
        }
        return false;
      }
      return status === "running" ? 2000 : false;
    }
  });

  const isRankingRunning = jobStatus?.status === "running" || rankingJobId;

  return (
    <div className="flex h-full w-64 flex-col bg-linear-to-b from-[#141926] to-[#0e1117] border-r border-[#2a3040]">
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-center border-b border-[#2a3040] px-4">
        <div className="flex items-center gap-2">
          <Shield className="h-8 w-8 text-[#00d4aa]" />
          <div>
            <span className="font-mono text-xl font-bold tracking-wider">
              <span className="text-[#00d4aa]">Aid</span>
              <span className="text-[#e8eaed]">Sec</span>
            </span>
            <p className="text-[0.65rem] uppercase tracking-[0.12em] text-[#b8bec6]">
              Lead Management
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-[#00d4aa33] text-[#00d4aa]"
                  : "text-[#b8bec6] hover:bg-[#00d4aa22] hover:text-[#e8eaed]"
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="flex-1">{item.name}</span>
              {item.name === "Ranking" && isRankingRunning && (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00d4aa] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00d4aa]"></span>
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="border-t border-[#2a3040] p-3">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-[#b8bec6] hover:bg-[#e74c3c22] hover:text-[#e74c3c] transition-colors"
        >
          <LogOut className="h-5 w-5" />
          Abmelden
        </button>
      </div>

      {/* Footer */}
      <div className="border-t border-[#2a3040] px-4 py-3">
        <p className="text-[0.7rem] text-[#6b728099] text-center font-mono tracking-wide">
          v2.1 · AidSec Dashboard
        </p>
      </div>
    </div>
  );
}
