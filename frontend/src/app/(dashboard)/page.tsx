"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi, analyticsApi, agentTasksApi } from "@/lib/api";
import {
  Users,
  Clock,
  CheckCircle2,
  Briefcase,
  Stethoscope,
  Globe,
  Zap,
  Server,
  Activity,
  ArrowUpRight,
  MessageSquareCode,
  Sparkles,
  MousePointer2,
  ArrowRight,
  Send,
  Target,
  LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import React from "react";

interface Task {
  id: number;
  task_type: string;
  lead_id: number;
  lead_firma: string | null;
  status: string;
  assigned_to: string | null;
  created_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export default function DashboardPage() {
  // Fetch overall KPIs
  const { data: kpis, isLoading: isKpisLoading } = useQuery({
    queryKey: ["dashboard-kpis"],
    queryFn: dashboardApi.getKpis,
    refetchInterval: 30000,
  });

  // Fetch Conversion Health
  const { data: health, isLoading: isHealthLoading } = useQuery({
    queryKey: ["conversion-health"],
    queryFn: () => analyticsApi.getConversionHealth(30),
  });

  // Fetch Agent Tasks
  const { data: tasks, isLoading: isTasksLoading } = useQuery({
    queryKey: ["agent-tasks"],
    queryFn: () => agentTasksApi.listTasks(5),
  });

  const isLoading = isKpisLoading || isHealthLoading || isTasksLoading;

  if (isLoading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center space-y-4">
        <div className="relative h-16 w-16">
          <div className="absolute inset-0 animate-ping rounded-full bg-[#00d4aa33]" />
          <div className="absolute inset-2 animate-pulse rounded-full bg-[#00d4aa66]" />
          <div className="absolute inset-4 rounded-full bg-[#00d4aa]" />
        </div>
        <p className="font-mono text-sm tracking-widest text-[#00d4aa] uppercase animate-pulse">
          Initializing Intelligence Systems...
        </p>
      </div>
    );
  }

  const stats = kpis?.status || {};
  const kategorie = kpis?.kategorie || {};
  const followups = kpis?.followups || { overdue: 0, today: 0, upcoming: 0 };
  const metrics = health?.metrics;

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-700">
      {/* Header with Glass Card */}
      <div className="relative overflow-hidden rounded-2xl border border-[#2a3040] bg-linear-to-br from-[#1a1f2e] to-[#0e1117] p-8 shadow-2xl">
        <div className="absolute -right-24 -top-24 h-64 w-64 bg-[#00d4aa11] blur-[100px] rounded-full" />
        <div className="absolute -left-24 -bottom-24 h-64 w-64 bg-[#3498db11] blur-[100px] rounded-full" />
        
        <div className="relative flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-[#00d4aa15] px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wider text-[#00d4aa] border border-[#00d4aa33]">
                <Sparkles className="h-3 w-3" /> System Active
              </span>
              <span className="text-[#6b728099] font-mono text-[0.65rem]">ID: AID-SEC-COMMAND-ALPHA</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-[#e8eaed]">
              Executive <span className="text-transparent bg-clip-text bg-linear-to-r from-[#e8eaed] to-[#00d4aa]">Command Center</span>
            </h1>
            <p className="mt-2 text-[#b8bec6] max-w-xl">
              Intelligent lead management and autonomous outreach orchestration for AidSec Cyber Security.
            </p>
          </div>
          
          <div className="flex flex-wrap gap-4">
            <div className="rounded-xl border border-[#2a3040] bg-[#0e1117]/50 px-4 py-2 backdrop-blur-sm">
              <p className="text-[0.6rem] uppercase tracking-wider text-[#b8bec6]">Conversion Rate</p>
              <p className="font-mono text-xl font-bold text-[#00d4aa]">{metrics?.conversion_rate || 0}%</p>
            </div>
            <div className="rounded-xl border border-[#2a3040] bg-[#0e1117]/50 px-4 py-2 backdrop-blur-sm">
              <p className="text-[0.6rem] uppercase tracking-wider text-[#b8bec6]">Reply Rate</p>
              <p className="font-mono text-xl font-bold text-[#3498db]">{metrics?.reply_rate || 0}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        
        {/* Left Column: Core Stats */}
        <div className="md:col-span-8 space-y-6">
          
          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard 
              label="Total Leads" 
              value={stats.total || 0} 
              icon={Users} 
              trend="+12%" 
              color="#3498db" 
            />
            <MetricCard 
              label="Open Deals" 
              value={stats.offen || 0} 
              icon={Activity} 
              color="#00d4aa" 
            />
            <MetricCard 
              label="Won Leads" 
              value={stats.gewonnen || 0} 
              icon={CheckCircle2} 
              color="#2ecc71" 
            />
            <MetricCard 
              label="Total Outreach" 
              value={metrics?.total_sent || 0} 
              icon={Send} 
              color="#9b59b6" 
            />
          </div>

          {/* Intelligence Pulse Section */}
          <div className="rounded-2xl border border-[#2a3040] bg-[#1a1f2e] overflow-hidden">
            <div className="border-b border-[#2a3040] bg-[#1a1f2e] px-6 py-4 flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-widest text-[#e8eaed] flex items-center gap-2">
                <Zap className="h-4 w-4 text-[#00d4aa]" /> Conversion Pipeline View
              </h3>
              <Link href="/analytics" className="text-[0.7rem] text-[#00d4aa] hover:underline flex items-center gap-1 font-mono uppercase">
                Detailed Report <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                   <p className="text-xs text-[#b8bec6] flex items-center gap-2">
                     <MousePointer2 className="h-3 w-3" /> Average Open Rate
                   </p>
                   <span className="font-mono text-sm text-[#00d4aa]">{metrics?.open_rate || 0}%</span>
                </div>
                <div className="h-2 w-full bg-[#0e1117] rounded-full overflow-hidden">
                  <div className="h-full bg-linear-to-r from-[#00d4aa33] to-[#00d4aa]" style={{ width: `${metrics?.open_rate || 0}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                   <p className="text-xs text-[#b8bec6] flex items-center gap-2">
                     <MessageSquareCode className="h-3 w-3" /> Engagement Index
                   </p>
                   <span className="font-mono text-sm text-[#3498db]">{metrics?.reply_rate || 0}%</span>
                </div>
                <div className="h-2 w-full bg-[#0e1117] rounded-full overflow-hidden">
                  <div className="h-full bg-linear-to-r from-[#3498db33] to-[#3498db]" style={{ width: `${metrics?.reply_rate || 0}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                   <p className="text-xs text-[#b8bec6] flex items-center gap-2">
                     <Target className="h-3 w-3" /> Success Conversion
                   </p>
                   <span className="font-mono text-sm text-[#2ecc71]">{metrics?.conversion_rate || 0}%</span>
                </div>
                <div className="h-2 w-full bg-[#0e1117] rounded-full overflow-hidden">
                  <div className="h-full bg-linear-to-r from-[#2ecc7133] to-[#2ecc71]" style={{ width: `${metrics?.conversion_rate || 0}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Categories Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CategoryCard label="Law Firms" value={kategorie.anwalt || 0} icon={Briefcase} color="#3498db" tagline="Kanzlei-Härtung" />
            <CategoryCard label="Practices" value={kategorie.praxis || 0} icon={Stethoscope} color="#9b59b6" tagline="Rapid Header Fix" />
            <CategoryCard label="WordPress" value={kategorie.wordpress || 0} icon={Globe} color="#e67e22" tagline="Rapid Header Fix" />
          </div>
        </div>

        {/* Right Column: Workforce & Activity */}
        <div className="md:col-span-4 space-y-6">
          
          {/* Agent Workforce Monitor */}
          <div className="rounded-2xl border border-[#2a3040] bg-linear-to-b from-[#1a1f2e] to-[#0e1117] p-6">
            <h3 className="text-sm font-bold uppercase tracking-widest text-[#e8eaed] mb-4 flex items-center gap-2">
              <Server className="h-4 w-4 text-[#00d4aa]" /> Agent Workforce
            </h3>
            
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-2 w-2 rounded-full bg-[#00d4aa] absolute -top-0.5 -right-0.5 animate-pulse" />
                  <div className="rounded-lg bg-[#00d4aa15] p-2">
                    <Sparkles className="h-5 w-5 text-[#00d4aa]" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#e8eaed]">Enrichment Agent</p>
                  <p className="text-[0.65rem] text-[#b8bec6] truncate font-mono">STATUS: SCANNING_ASSETS</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-2 w-2 rounded-full bg-[#3498db] absolute -top-0.5 -right-0.5" />
                  <div className="rounded-lg bg-[#3498db15] p-2">
                    <Send className="h-5 w-5 text-[#3498db]" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#e8eaed]">Outreach Agent</p>
                  <p className="text-[0.65rem] text-[#b8bec6] truncate font-mono">STATUS: WAITING_FOR_APPROVAL</p>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-[#2a3040]">
              <p className="text-[0.6rem] uppercase tracking-wider text-[#6b7280] mb-3">Live Task Queue</p>
              <div className="space-y-3">
                {tasks?.map((task: Task) => (
                  <div key={task.id} className="flex items-center justify-between text-[0.7rem]">
                    <span className="text-[#b8bec6] truncate max-w-[120px]">{task.lead_firma || 'System'}</span>
                    <span className={cn(
                      "px-1.5 py-0.5 rounded font-mono border",
                      task.status === 'completed' ? "bg-[#2ecc7115] text-[#2ecc71] border-[#2ecc7133]" :
                      task.status === 'failed' ? "bg-[#e74c3c15] text-[#e74c3c] border-[#e74c3c33]" :
                      "bg-[#f39c1215] text-[#f39c12] border-[#f39c1233]"
                    )}>
                      {task.status.toUpperCase()}
                    </span>
                  </div>
                ))}
                {(!tasks || tasks.length === 0) && (
                   <p className="text-center py-2 text-[#6b7280] text-[0.7rem] italic">Queue is currently empty</p>
                )}
              </div>
              <Link href="/tasks" className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#2a3040] py-2 text-[0.65rem] font-bold uppercase tracking-tight text-[#e8eaed] hover:bg-[#344054] transition-colors">
                Open Full Workforce <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>

          {/* Urgent Follow-ups */}
          {(followups.overdue > 0 || followups.today > 0) && (
             <div className="rounded-2xl border border-[#e74c3c33] bg-[#e74c3c05] p-6 backdrop-blur-md">
               <h3 className="text-sm font-bold uppercase tracking-widest text-[#e8eaed] mb-4 flex items-center gap-2">
                <Clock className="h-4 w-4 text-[#e74c3c]" /> Attention Required
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#e74c3c15] border border-[#e74c3c33] p-3 rounded-xl">
                  <p className="text-[0.6rem] uppercase tracking-wider text-[#f09a92]">Overdue</p>
                  <p className="text-2xl font-mono font-bold text-[#e74c3c]">{followups.overdue}</p>
                </div>
                <div className="bg-[#f39c1215] border border-[#f39c1233] p-3 rounded-xl">
                  <p className="text-[0.6rem] uppercase tracking-wider text-[#f7c56e]">Today</p>
                  <p className="text-2xl font-mono font-bold text-[#f39c12]">{followups.today}</p>
                </div>
              </div>
              <Link href="/leads" className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#e74c3c22] py-2 text-[0.65rem] font-bold uppercase tracking-tight text-[#e8eaed] hover:bg-[#e74c3c44] transition-colors">
                Resolve Now <Zap className="h-3 w-3" />
              </Link>
             </div>
          )}

        </div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  color: string;
}

function MetricCard({ label, value, icon: Icon, trend, color }: MetricCardProps) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-[#2a3040] bg-[#1a1f2e] p-5 transition-all duration-300 hover:border-[#00d4aa33] hover:shadow-[0_0_20px_rgba(0,212,170,0.05)]">
      <div className="flex items-center justify-between mb-2">
        <div className="rounded-lg bg-[#0e1117] p-2">
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        {trend && (
          <span className="text-[0.65rem] font-mono text-[#2ecc71] flex items-center bg-[#2ecc7110] px-1.5 py-0.5 rounded">
             {trend}
          </span>
        )}
      </div>
      <p className="text-[0.65rem] uppercase tracking-widest text-[#b8bec6] mb-1 font-medium">{label}</p>
      <p className="font-mono text-2xl font-bold text-[#e8eaed]">{value}</p>
      <div 
        className="absolute -right-4 -bottom-4 opacity-5 transition-transform duration-500 group-hover:scale-110 group-hover:rotate-6"
        style={{ color }}
      >
        <Icon className="h-16 w-16" />
      </div>
    </div>
  );
}

interface CategoryCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  color: string;
  tagline: string;
}

function CategoryCard({ label, value, icon: Icon, color, tagline }: CategoryCardProps) {
  return (
    <div className="flex flex-col rounded-2xl border border-[#2a3040] bg-[#1a1f2e] p-4 group transition-colors hover:bg-[#1a1f2e]/80">
      <div className="flex items-center gap-3 mb-3">
        <div className="rounded-xl p-2.5 transition-transform group-hover:scale-110" style={{ backgroundColor: `${color}15` }}>
          <Icon className="h-5 w-5" style={{ color }} />
        </div>
        <div>
          <p className="text-xs font-bold text-[#e8eaed] uppercase tracking-tight">{label}</p>
          <p className="text-[0.6rem] text-[#6b7280] italic">{tagline}</p>
        </div>
      </div>
      <div className="flex items-end justify-between mt-auto">
        <p className="font-mono text-3xl font-bold text-[#e8eaed]">{value}</p>
        <div className="h-1 w-16 bg-[#0e1117] rounded-full overflow-hidden">
           <div className="h-full opacity-50 transition-all duration-1000" style={{ backgroundColor: color, width: '60%' }} />
        </div>
      </div>
    </div>
  );
}
