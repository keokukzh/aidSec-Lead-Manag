"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { campaignsApi, emailsApi, agentTasksApi, leadsApi } from "@/lib/api";
import { Loader2, AlertCircle, ArrowRightLeft, Mail, Server, Sparkles } from "lucide-react";

interface CampaignItem {
  id: number;
  name: string;
  status: string;
  leads_count?: number;
  completed_count?: number;
}

interface SequenceItem {
  id: number;
  name: string;
  status: string;
  steps: Array<{ day_offset: number }>;
}

interface AgentTaskItem {
  id: number;
  task_type: string;
  status: string;
  lead_firma?: string | null;
}

export default function OutreachControlPage() {
  const { data: campaigns, isLoading: campaignsLoading, error: campaignsError } = useQuery({
    queryKey: ["campaigns", "outreach-control"],
    queryFn: () => campaignsApi.list(),
  });

  const { data: sequences, isLoading: sequencesLoading, error: sequencesError } = useQuery({
    queryKey: ["sequences", "outreach-control"],
    queryFn: () => emailsApi.listSequences(),
  });

  const { data: dueCount, isLoading: dueCountLoading } = useQuery({
    queryKey: ["sequence-due", "outreach-control"],
    queryFn: () => emailsApi.getSequenceExecutionDueCount(),
  });

  const { data: drafts, isLoading: draftsLoading } = useQuery({
    queryKey: ["drafts", "outreach-control"],
    queryFn: () => emailsApi.listDrafts(),
  });

  const { data: tasks, isLoading: tasksLoading } = useQuery({
    queryKey: ["tasks", "outreach-control"],
    queryFn: () => agentTasksApi.listTasks(200),
  });

  const { data: conflicts, isLoading: conflictsLoading } = useQuery({
    queryKey: ["orchestration-conflicts", "outreach-control"],
    queryFn: () => leadsApi.getOrchestrationConflicts(),
  });

  const isLoading = campaignsLoading || sequencesLoading || dueCountLoading || draftsLoading || tasksLoading || conflictsLoading;
  const isError = campaignsError || sequencesError;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-2 h-8 w-8 text-[#e74c3c]" />
          <p className="text-[#e74c3c]">Outreach Control konnte nicht geladen werden</p>
        </div>
      </div>
    );
  }

  const campaignList = (campaigns as CampaignItem[]) || [];
  const sequenceList = (sequences as SequenceItem[]) || [];
  const taskList = (tasks as AgentTaskItem[]) || [];
  const draftList = drafts || [];

  const activeCampaigns = campaignList.filter((c) => c.status === "aktiv").length;
  const activeSequences = sequenceList.filter((s) => s.status === "aktiv").length;
  const campaignLeadsTotal = campaignList.reduce((sum, c) => sum + (c.leads_count || 0), 0);
  const sequenceStepsTotal = sequenceList.reduce((sum, s) => sum + (s.steps?.length || 0), 0);

  const pendingTasks = taskList.filter((t) => t.status === "pending" || t.status === "processing").length;
  const failedTasks = taskList.filter((t) => t.status === "failed" || t.status === "error").length;
  const dueSequenceAssignments = dueCount?.due_count || 0;
  const conflictCount = conflicts?.count || 0;

  const handoffHealth = {
    campaignToAgent: pendingTasks > 25 ? "backlog" : "ok",
    agentToDraft: draftList.length > 30 ? "backlog" : "ok",
    draftToSequence: dueSequenceAssignments > 50 ? "backlog" : "ok",
  } as const;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">Outreach Control</h1>
        <p className="text-[#b8bec6]">Dual-Track Steuerung mit klaren Grenzen und Handoff-Status.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-[#2a3040] bg-[#1a1f2e] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-[#e8eaed]">
              <Server className="h-4 w-4 text-[#3498db]" /> Campaign Track
            </h2>
            <Link href="/kampagnen" className="text-xs text-[#00d4aa] hover:underline">Öffnen</Link>
          </div>
          <p className="mb-4 text-xs text-[#b8bec6]">
            Boundary: Kampagnen planen den Outreach; fällige Schritte werden als Agent-Tasks in die Queue übergeben.
          </p>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Active" value={activeCampaigns} color="text-[#3498db]" />
            <Stat label="Leads" value={campaignLeadsTotal} color="text-[#e8eaed]" />
            <Stat label="Queue" value={pendingTasks} color="text-[#f39c12]" />
          </div>
        </div>

        <div className="rounded-2xl border border-[#2a3040] bg-[#1a1f2e] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-[#e8eaed]">
              <Mail className="h-4 w-4 text-[#00d4aa]" /> Sequence Track
            </h2>
            <Link href="/email" className="text-xs text-[#00d4aa] hover:underline">Öffnen</Link>
          </div>
          <p className="mb-4 text-xs text-[#b8bec6]">
            Boundary: Sequences laufen im Worker-Flow mit Assignments; fällige Assignments gehen direkt in den Versandlauf.
          </p>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Active" value={activeSequences} color="text-[#00d4aa]" />
            <Stat label="Steps" value={sequenceStepsTotal} color="text-[#e8eaed]" />
            <Stat label="Due" value={dueSequenceAssignments} color="text-[#f39c12]" />
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-[#2a3040] bg-[#1a1f2e] p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-[#e8eaed]">
          <ArrowRightLeft className="h-4 w-4 text-[#00d4aa]" /> Handoff Indicators
        </h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <HandoffCard
            title="Campaign → Agent Queue"
            detail={`${pendingTasks} pending/processing tasks`}
            state={handoffHealth.campaignToAgent}
            href="/tasks"
          />
          <HandoffCard
            title="Agent → Draft Approval"
            detail={`${draftList.length} drafts waiting`}
            state={handoffHealth.agentToDraft}
            href="/drafts"
          />
          <HandoffCard
            title="Draft → Sequence Execution"
            detail={`${dueSequenceAssignments} due assignments`}
            state={handoffHealth.draftToSequence}
            href="/email"
          />
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <QuickLink href="/kampagnen" label="Manage Campaigns" />
          <QuickLink href="/email" label="Manage Sequences" />
          <QuickLink href="/tasks" label={`Investigate Failures (${failedTasks})`} />
        </div>
      </div>

      {conflictCount > 0 && (
        <div className="rounded-2xl border border-[#e74c3c33] bg-[#e74c3c0d] p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-[#e8eaed]">
            Guardrail Alert: Dual-Track Conflicts
          </h2>
          <p className="mb-3 text-sm text-[#f0b7b1]">
            {conflictCount} Leads sind gleichzeitig aktiv in Campaign + Sequence. Bitte einen Track pausieren oder entfernen.
          </p>
          <div className="space-y-2">
            {(conflicts?.sample || []).slice(0, 8).map((lead) => (
              <div key={lead.id} className="flex items-center justify-between rounded border border-[#2a3040] bg-[#0e1117]/60 px-3 py-2 text-xs">
                <span className="text-[#e8eaed]">{lead.firma || `Lead #${lead.id}`}</span>
                <span className="text-[#b8bec6]">{lead.status}</span>
              </div>
            ))}
          </div>
          <div className="mt-4">
            <Link href="/leads?sort=stale_first" className="text-xs text-[#00d4aa] hover:underline">
              Open Leads Queue for Conflict Resolution
            </Link>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-[#2a3040] bg-[#1a1f2e] p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-[#e8eaed]">
          <Sparkles className="h-4 w-4 text-[#00d4aa]" /> Operational Summary
        </h2>
        <ul className="space-y-2 text-sm text-[#b8bec6]">
          <li>• Active Campaigns: <span className="text-[#e8eaed]">{activeCampaigns}</span> · Active Sequences: <span className="text-[#e8eaed]">{activeSequences}</span></li>
          <li>• Draft Approval Queue: <span className="text-[#e8eaed]">{draftList.length}</span> · Failed Agent Tasks: <span className="text-[#e8eaed]">{failedTasks}</span></li>
          <li>• Sequence Due Assignments: <span className="text-[#e8eaed]">{dueSequenceAssignments}</span></li>
        </ul>
      </div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg border border-[#2a3040] bg-[#0e1117]/60 p-3">
      <p className="text-[0.65rem] uppercase tracking-wider text-[#b8bec6]">{label}</p>
      <p className={`mt-1 text-xl font-mono font-bold ${color}`}>{value}</p>
    </div>
  );
}

function HandoffCard({
  title,
  detail,
  state,
  href,
}: {
  title: string;
  detail: string;
  state: "ok" | "backlog";
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border border-[#2a3040] bg-[#0e1117]/60 p-4 hover:border-[#00d4aa]"
    >
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#e8eaed]">{title}</p>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
            state === "ok"
              ? "bg-[#2ecc7115] text-[#2ecc71]"
              : "bg-[#e74c3c15] text-[#e74c3c]"
          }`}
        >
          {state}
        </span>
      </div>
      <p className="text-sm text-[#b8bec6]">{detail}</p>
    </Link>
  );
}

function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-[#2a3040] bg-[#0e1117]/60 px-3 py-2 text-center text-xs font-medium text-[#b8bec6] hover:border-[#00d4aa] hover:text-[#e8eaed]"
    >
      {label}
    </Link>
  );
}
