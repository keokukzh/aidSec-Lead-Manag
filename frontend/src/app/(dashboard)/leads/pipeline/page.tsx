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

type LeadStatus = "offen" | "pending" | "gewonnen" | "verloren";

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
}

interface PipelineData {
  offen: { items: Lead[]; total: number };
  pending: { items: Lead[]; total: number };
  gewonnen: { items: Lead[]; total: number };
  verloren: { items: Lead[]; total: number };
}

const statusConfig: Record<
  LeadStatus,
  { label: string; color: string; bgColor: string }
> = {
  offen: { label: "Offen", color: "text-[#f59e0b]", bgColor: "bg-[#f59e0b]" },
  pending: {
    label: "Pending",
    color: "text-[#3b82f6]",
    bgColor: "bg-[#3b82f6]",
  },
  gewonnen: {
    label: "Gewonnen",
    color: "text-[#00d4aa]",
    bgColor: "bg-[#00d4aa]",
  },
  verloren: {
    label: "Verloren",
    color: "text-[#6b7280]",
    bgColor: "bg-[#6b7280]",
  },
};

const statuses: LeadStatus[] = ["offen", "pending", "gewonnen", "verloren"];



export default function PipelinePage() {
  const queryClient = useQueryClient();
  const [draggedLead, setDraggedLead] = useState<Lead | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<LeadStatus | null>(null);

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

  const pipeline: PipelineData = (data as unknown as PipelineData) || {
    offen: { items: [], total: 0 },
    pending: { items: [], total: 0 },
    gewonnen: { items: [], total: 0 },
    verloren: { items: [], total: 0 },
  };

  const handleDragStart = (e: React.DragEvent, lead: Lead) => {
    setDraggedLead(lead);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", lead.id.toString());
  };

  const handleDragOver = (e: React.DragEvent, status: LeadStatus) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverColumn(status);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = (e: React.DragEvent, newStatus: LeadStatus) => {
    e.preventDefault();
    setDragOverColumn(null);

    if (!draggedLead) return;

    if (draggedLead.status !== newStatus) {
      updateStatusMutation.mutate({
        leadId: draggedLead.id,
        status: newStatus,
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
        {statuses.map((status) => {
          const config = statusConfig[status];
          const columnData = pipeline[status];
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
                        <GripVertical className="mt-1 h-4 w-4 flex-shrink-0 cursor-grab text-[#6b7280] opacity-0 transition-opacity group-hover:opacity-100" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium text-[#e8eaed]">
                              {lead.firma}
                            </span>
                            {lead.ranking_grade && (
                              <span
                                className={cn(
                                  "flex-shrink-0 rounded px-1.5 py-0.5 text-xs font-bold",
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
        {statuses.map((status) => (
          <div key={status} className="flex items-center gap-2">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                statusConfig[status].bgColor,
              )}
            />
            <span>{statusConfig[status].label}:</span>
            <span className="font-medium text-[#e8eaed]">
              {pipeline[status].total}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
