"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { agentTasksApi } from "@/lib/api";
import { Loader2, Server, CheckCircle2, XCircle, Clock, Activity, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { de } from "date-fns/locale";

export default function AgentTasksPage() {
  const [mode, setMode] = useState<"active" | "history">("active");

  const { data: activeTasks, isLoading: activeLoading, error: activeError } = useQuery({
    queryKey: ["agentTasks", "active"],
    queryFn: () => agentTasksApi.listActiveTasks(150),
    refetchInterval: 10000,
  });

  const { data: historyTasks, isLoading: historyLoading, error: historyError } = useQuery({
    queryKey: ["agentTasks", "history"],
    queryFn: () => agentTasksApi.listTaskHistory(150),
    refetchInterval: 10000, // Poll every 10s
  });

  const isLoading = mode === "active" ? activeLoading : historyLoading;
  const error = mode === "active" ? activeError : historyError;
  const taskList = mode === "active" ? (activeTasks || []) : (historyTasks || []);

  const pendingCount = (activeTasks || []).filter((t) => t.status === "pending").length;
  const processingCount = (activeTasks || []).filter((t) => t.status === "processing").length;
  const deadLetterCount = (historyTasks || []).filter((t) => t.status === "dead_letter").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">OpenClaw Queue</h1>
          <p className="text-[#b8bec6]">Operations-first queue view for active work and execution history</p>
        </div>
        <div className="flex items-center gap-2 rounded-md bg-[#2a3040] px-4 py-2 text-sm font-medium text-[#e8eaed]">
          <Activity className="h-4 w-4 text-[#00d4aa] animate-pulse" />
          Live Connection
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3">
        <button
          onClick={() => setMode("active")}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-semibold transition-colors",
            mode === "active"
              ? "bg-[#00d4aa22] text-[#00d4aa] border border-[#00d4aa55]"
              : "bg-[#2a3040] text-[#b8bec6] hover:text-[#e8eaed]"
          )}
        >
          Active Queue ({(activeTasks || []).length})
        </button>
        <button
          onClick={() => setMode("history")}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-semibold transition-colors",
            mode === "history"
              ? "bg-[#00d4aa22] text-[#00d4aa] border border-[#00d4aa55]"
              : "bg-[#2a3040] text-[#b8bec6] hover:text-[#e8eaed]"
          )}
        >
          History ({(historyTasks || []).length})
        </button>

        <div className="ml-auto flex items-center gap-2 text-[11px] text-[#b8bec6]">
          <span className="rounded bg-[#2a3040] px-2 py-1">pending: {pendingCount}</span>
          <span className="rounded bg-[#2a3040] px-2 py-1">processing: {processingCount}</span>
          <span className="rounded bg-[#2a3040] px-2 py-1">dead letter: {deadLetterCount}</span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
        </div>
      ) : error ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <AlertCircle className="mx-auto mb-2 h-8 w-8 text-[#e74c3c]" />
            <p className="text-[#e74c3c]">Failed to load tasks</p>
          </div>
        </div>
      ) : taskList.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-[#2a3040] bg-[#1a1f2e]">
          <Server className="mb-4 h-12 w-12 text-[#b8bec6]" />
          <p className="text-[#b8bec6]">{mode === "active" ? "Active queue is empty" : "No history items"}</p>
          <p className="mt-1 text-sm text-[#6b728099]">
            {mode === "active" ? "No pending/processing tasks right now" : "Completed/failed/dead-letter tasks will appear here"}
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-[#b8bec6]">
              <thead className="bg-[#141926] text-xs uppercase text-[#6b7280]">
                <tr>
                  <th className="px-6 py-4 font-semibold">ID / Lead</th>
                  <th className="px-6 py-4 font-semibold">Task Type</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold">Agent Node</th>
                  <th className="px-6 py-4 font-semibold">Attempts</th>
                  <th className="px-6 py-4 font-semibold text-right">Age</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a3040]">
                {taskList.map((task) => (
                  <tr key={task.id} className="transition-colors hover:bg-[#141926]">
                    <td className="whitespace-nowrap px-6 py-4">
                      <div className="font-medium text-[#e8eaed]">#{task.id}</div>
                      <div className="text-xs">{task.lead_firma || 'Unknown Lead'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="rounded bg-[#2a3040] px-2 py-1 text-xs font-mono text-[#00d4aa]">
                        {task.task_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {task.status === "completed" ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        ) : task.status === "failed" ? (
                          <XCircle className="h-4 w-4 text-[#e74c3c]" />
                        ) : task.status === "processing" ? (
                          <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
                        ) : (
                          <Clock className="h-4 w-4 text-orange-400" />
                        )}
                        <span className={cn(
                          "capitalize",
                          task.status === "completed" && "text-emerald-500",
                          task.status === "failed" && "text-[#e74c3c]",
                          task.status === "processing" && "text-blue-400 font-medium",
                          task.status === "pending" && "text-orange-400",
                        )}>
                          {task.status}
                        </span>
                      </div>
                      {task.error_message && (
                        <div className="mt-1 text-xs text-[#e74c3c] break-all max-w-[200px] truncate" title={task.error_message}>
                          {task.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs">
                       {task.assigned_to || <span className="text-muted-foreground">-</span>}
                    </td>
                      <td className="px-6 py-4 font-mono text-xs text-[#b8bec6]">
                       {task.attempts ?? 0}/{task.max_attempts ?? 5}
                      </td>
                    <td className="px-6 py-4 text-right">
                       {task.created_at ? formatDistanceToNow(new Date(task.created_at), { addSuffix: true, locale: de }) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
