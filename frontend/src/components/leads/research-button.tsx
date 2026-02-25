"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi } from "@/lib/api";
import {
  Search,
  Loader2,
  Check,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

interface ResearchButtonProps {
  leadId: number;
  website: string | null;
  researchStatus?: string | null;
  onSuccess?: () => void;
}

export function ResearchButton({
  leadId,
  website,
  researchStatus,
  onSuccess,
}: ResearchButtonProps) {
  const queryClient = useQueryClient();
  const [showResult, setShowResult] = useState(false);

  const mutation = useMutation({
    mutationFn: () => leadsApi.research(leadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead", leadId] });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setShowResult(true);
      setTimeout(() => setShowResult(false), 5000);
      onSuccess?.();
    },
  });

  if (!website) {
    return (
      <span className="text-xs text-[#6b7280]">
        Keine Website verfügbar
      </span>
    );
  }

  const isPending = mutation.isPending;
  const isCompleted = researchStatus === "completed";
  const isFailed = researchStatus === "failed";

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => mutation.mutate()}
        disabled={isPending}
        className="flex items-center gap-1.5 rounded-md border border-[#2a3040] bg-[#1a1f2e] px-3 py-1.5 text-sm text-[#e8eaed] transition-all hover:border-[#00d4aa] disabled:opacity-50"
      >
        {isPending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin text-[#00d4aa]" />
            <span>Recherchiere...</span>
          </>
        ) : (
          <>
            <Search className="h-4 w-4" />
            <span>Recherchieren</span>
          </>
        )}
      </button>

      {showResult && mutation.data && (
        <div className="flex items-center gap-1 text-sm">
          {mutation.data.status === "completed" ? (
            <span className="flex items-center gap-1 text-[#00d4aa]">
              <Check className="h-4 w-4" />
              Daten gefunden!
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[#f59e0b]">
              <AlertCircle className="h-4 w-4" />
              Keine neuen Daten
            </span>
          )}
        </div>
      )}

      {researchStatus && !showResult && (
        <span className="text-xs text-[#6b7280]">
          {isCompleted && (
            <span className="flex items-center gap-1 text-[#00d4aa]">
              <Check className="h-3 w-3" />
              Recherchiert
            </span>
          )}
          {isFailed && (
            <span className="flex items-center gap-1 text-[#e74c3c]">
              <AlertCircle className="h-3 w-3" />
              Fehlgeschlagen
            </span>
          )}
          {researchStatus === "in_progress" && (
            <span className="flex items-center gap-1 text-[#3b82f6]">
              <RefreshCw className="h-3 w-3 animate-spin" />
              Läuft...
            </span>
          )}
        </span>
      )}
    </div>
  );
}

// Bulk research button for multiple leads
interface BulkResearchButtonProps {
  leadIds: number[];
  onSuccess?: () => void;
}

export function BulkResearchButton({ leadIds, onSuccess }: BulkResearchButtonProps) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => leadsApi.bulkResearch(leadIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      onSuccess?.();
    },
  });

  return (
    <button
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending || leadIds.length === 0}
      className="flex items-center gap-1.5 rounded-md bg-[#00d4aa] px-3 py-1.5 text-sm font-semibold text-[#0e1117] transition-all hover:bg-[#00e8bb] disabled:opacity-50"
    >
      {mutation.isPending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Recherchiere...</span>
        </>
      ) : (
        <>
          <Search className="h-4 w-4" />
          <span>{leadIds.length} Leads recherchieren</span>
        </>
      )}
    </button>
  );
}

// Research missing leads button
interface ResearchMissingButtonProps {
  onSuccess?: () => void;
}

export function ResearchMissingButton({ onSuccess }: ResearchMissingButtonProps) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (limit: number) => leadsApi.researchMissing(limit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      onSuccess?.();
    },
  });

  return (
    <button
      onClick={() => mutation.mutate(20)}
      disabled={mutation.isPending}
      className="flex items-center gap-1.5 rounded-md border border-[#2a3040] bg-[#1a1f2e] px-3 py-1.5 text-sm text-[#e8eaed] transition-all hover:border-[#00d4aa] disabled:opacity-50"
    >
      {mutation.isPending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin text-[#00d4aa]" />
          <span>Recherchiere...</span>
        </>
      ) : (
        <>
          <Search className="h-4 w-4" />
          <span>Fehlende Daten recherchieren</span>
        </>
      )}
    </button>
  );
}
