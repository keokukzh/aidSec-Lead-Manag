"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { leadsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Loader2,
  AlertCircle,
  GripVertical,
  ChevronRight,
  RefreshCw,
} from "lucide-react";

type LeadStatus =
  | "offen"
  | "pending"
  | "response_received"
  | "offer_sent"
  | "negotiation"
  | "gewonnen"
  | "verloren";

type PrimaryPipelineStatus = "intake" | "outreach" | "won" | "lost";

interface Lead {
  id: number;
  firma: string;
  email: string;
  telefon: string;
  stadt: string;
  kategorie: string;
  status: LeadStatus;
  ranking_grade: string;
  ranking_score: number;
  quelle: string;
  created_at?: string;
}

type PipelineData = Record<LeadStatus, { items: Lead[]; total: number }>;

const statusConfig: Record<
  PrimaryPipelineStatus,
  { label: string; color: string; bgColor: string }
> = {
  intake: { label: "Intake", color: "text-[#f59e0b]", bgColor: "bg-[#f59e0b]" },
  outreach: {
    label: "Outreach aktiv",
    color: "text-[#3b82f6]",
    bgColor: "bg-[#3b82f6]",
  },
  won: {
    label: "Gewonnen",
    color: "text-[#00d4aa]",
    bgColor: "bg-[#00d4aa]",
  },
  lost: {
    label: "Verloren",
    color: "text-[#6b7280]",
    bgColor: "bg-[#6b7280]",
  },
};

const primaryStatuses: PrimaryPipelineStatus[] = ["intake", "outreach", "won", "lost"];

const subStatusLabel: Record<LeadStatus, string> = {
  offen: "offen",
  pending: "pending",
  response_received: "response",
  offer_sent: "angebot",
  negotiation: "verhandlung",
  gewonnen: "gewonnen",
  verloren: "verloren",
};

const mapLeadToPrimary = (status: LeadStatus): PrimaryPipelineStatus => {
  if (status === "gewonnen") return "won";
  if (status === "verloren") return "lost";
  if (
    status === "pending" ||
    status === "response_received" ||
    status === "offer_sent" ||
    status === "negotiation"
  ) {
    return "outreach";
  }
  return "intake";
};

const mapPrimaryToTargetStatus = (status: PrimaryPipelineStatus): LeadStatus => {
  if (status === "intake") return "offen";
  if (status === "won") return "gewonnen";
  if (status === "lost") return "verloren";
  return "pending";
};

const emptyPipeline: PipelineData = {
  offen: { items: [], total: 0 },
  pending: { items: [], total: 0 },
  response_received: { items: [], total: 0 },
  offer_sent: { items: [], total: 0 },
  negotiation: { items: [], total: 0 },
  gewonnen: { items: [], total: 0 },
  verloren: { items: [], total: 0 },
};

function buildPrimaryPipeline(pipeline: PipelineData) {
  const grouped: Record<
    PrimaryPipelineStatus,
    { items: Lead[]; total: number; subTotals: Record<LeadStatus, number> }
  > = {
    intake: { items: [], total: 0, subTotals: { ...Object.fromEntries(Object.keys(emptyPipeline).map((k) => [k, 0])) } as Record<LeadStatus, number> },
    outreach: { items: [], total: 0, subTotals: { ...Object.fromEntries(Object.keys(emptyPipeline).map((k) => [k, 0])) } as Record<LeadStatus, number> },
    won: { items: [], total: 0, subTotals: { ...Object.fromEntries(Object.keys(emptyPipeline).map((k) => [k, 0])) } as Record<LeadStatus, number> },
    lost: { items: [], total: 0, subTotals: { ...Object.fromEntries(Object.keys(emptyPipeline).map((k) => [k, 0])) } as Record<LeadStatus, number> },
  };

  (Object.keys(pipeline) as LeadStatus[]).forEach((status) => {
    const primary = mapLeadToPrimary(status);
    grouped[primary].items.push(...(pipeline[status]?.items || []));
    grouped[primary].total += pipeline[status]?.total || 0;
    grouped[primary].subTotals[status] = pipeline[status]?.total || 0;
  });

  (Object.keys(grouped) as PrimaryPipelineStatus[]).forEach((primary) => {
    grouped[primary].items.sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bTime - aTime;
    });
  });

  return grouped;
}



export default function PipelinePage() {
  const queryClient = useQueryClient();
  const [draggedLead, setDraggedLead] = useState<Lead | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<PrimaryPipelineStatus | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["pipeline"],
    queryFn: () => leadsApi.getPipeline(50),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ leadId, status }: { leadId: number; status: string }) =>
      leadsApi.update(leadId.toString(), { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
    },
  });

  const pipeline: PipelineData = (data as PipelineData) || emptyPipeline;
  const primaryPipeline = buildPrimaryPipeline(pipeline);

  const handleDragStart = (e: React.DragEvent, lead: Lead) => {
    setDraggedLead(lead);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", lead.id.toString());
  };

  const handleDragOver = (e: React.DragEvent, status: PrimaryPipelineStatus) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverColumn(status);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = (e: React.DragEvent, newStatus: PrimaryPipelineStatus) => {
    e.preventDefault();
    setDragOverColumn(null);

    if (!draggedLead) return;

    const targetStatus = mapPrimaryToTargetStatus(newStatus);
    if (mapLeadToPrimary(draggedLead.status) !== newStatus || draggedLead.status !== targetStatus) {
      updateStatusMutation.mutate({
        leadId: draggedLead.id,
        status: targetStatus,
      });
    }

    setDraggedLead(null);
  };

  const handleDragEnd = () => {
    setDraggedLead(null);
    setDragOverColumn(null);
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-2 h-8 w-8 text-[#e74c3c]" />
          <p className="text-[#e74c3c]">Fehler beim Laden der Pipeline</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Pipeline</h1>
          <p className="text-[#b8bec6]">
            Lead-Status Übersicht mit Drag & Drop
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 rounded-md border border-[#2a3040] bg-[#1a1f2e] px-4 py-2 text-[#e8eaed] transition-all hover:bg-[#2a3040]"
        >
          <RefreshCw className="h-4 w-4" />
          Aktualisieren
        </button>
      </div>

      {/* Pipeline Columns */}
      <div className="grid grid-cols-4 gap-4">
        {primaryStatuses.map((status) => {
          const config = statusConfig[status];
          const columnData = primaryPipeline[status];
          const isDragOver = dragOverColumn === status;

          return (
            <div
              key={status}
              className={cn(
                "flex flex-col rounded-lg border bg-[#1a1f2e] transition-colors",
                isDragOver ? "border-[#00d4aa]" : "border-[#2a3040]",
              )}
              onDragOver={(e) => handleDragOver(e, status)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, status)}
            >
              {/* Column Header */}
              <div className="flex items-center justify-between rounded-t-lg border-b border-[#2a3040] bg-[#141926] p-4">
                <div className="flex items-center gap-2">
                  <div className={cn("h-2 w-2 rounded-full", config.bgColor)} />
                  <span className="font-medium text-[#e8eaed]">
                    {config.label}
                  </span>
                </div>
                <span className="rounded-full bg-[#2a3040] px-2 py-0.5 text-xs text-[#b8bec6]">
                  {columnData.total}
                </span>
              </div>
              <div className="flex flex-wrap gap-1 border-b border-[#2a3040] px-4 py-2">
                {(Object.keys(columnData.subTotals) as LeadStatus[])
                  .filter((sub) => columnData.subTotals[sub] > 0)
                  .map((sub) => (
                    <span
                      key={sub}
                      className="rounded bg-[#2a3040] px-1.5 py-0.5 text-[10px] text-[#b8bec6]"
                    >
                      {subStatusLabel[sub]}: {columnData.subTotals[sub]}
                    </span>
                  ))}
              </div>

              {/* Column Content */}
              <div
                className="flex-1 space-y-2 overflow-y-auto p-2 max-h-[calc(100vh-300px)]"
              >
                {columnData.items.length === 0 ? (
                  <div className="py-8 text-center text-sm text-[#6b7280]">
                    Keine Leads
                  </div>
                ) : (
                  columnData.items.map((lead) => (
                    <div
                      key={lead.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, lead)}
                      onDragEnd={handleDragEnd}
                      className={cn(
                        "group cursor-grab rounded-lg border border-[#2a3040] bg-[#141926] p-3 transition-all hover:border-[#00d4aa]",
                        draggedLead?.id === lead.id && "opacity-50",
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <GripVertical className="mt-1 h-4 w-4 shrink-0 cursor-grab text-[#6b7280] opacity-0 transition-opacity group-hover:opacity-100" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium text-[#e8eaed]">
                              {lead.firma}
                            </span>
                            {lead.ranking_grade && (
                              <span
                                className={cn(
                                  "shrink-0 rounded px-1.5 py-0.5 text-xs font-bold",
                                  lead.ranking_grade === "A" &&
                                    "bg-green-900 text-green-300",
                                  lead.ranking_grade === "B" &&
                                    "bg-yellow-900 text-yellow-300",
                                  lead.ranking_grade === "C" &&
                                    "bg-red-900 text-red-300",
                                  !["A", "B", "C"].includes(
                                    lead.ranking_grade || "",
                                  ) && "bg-gray-700 text-gray-300",
                                )}
                              >
                                {lead.ranking_grade}
                              </span>
                            )}
                            {lead.status && lead.status !== mapPrimaryToTargetStatus(status) && (
                              <span className="rounded bg-[#2a3040] px-1.5 py-0.5 text-[10px] text-[#b8bec6]">
                                {subStatusLabel[lead.status] || lead.status}
                              </span>
                            )}
                          </div>
                          <div className="mt-1 truncate text-sm text-[#b8bec6]">
                            {lead.email || lead.stadt || "—"}
                          </div>
                          <div className="mt-2 flex items-center justify-between">
                            <span className="text-xs capitalize text-[#6b7280]">
                              {lead.kategorie || "—"}
                            </span>
                            <Link
                              href={`/leads/${lead.id}`}
                              className="flex items-center gap-1 text-xs text-[#00d4aa] opacity-0 transition-opacity group-hover:opacity-100 hover:underline"
                            >
                              Ansehen
                              <ChevronRight className="h-3 w-3" />
                            </Link>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div className="flex items-center justify-center gap-8 text-sm text-[#b8bec6]">
        {primaryStatuses.map((status) => (
          <div key={status} className="flex items-center gap-2">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                statusConfig[status].bgColor,
              )}
            />
            <span>{statusConfig[status].label}:</span>
            <span className="font-medium text-[#e8eaed]">
              {primaryPipeline[status].total}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
