"use client";

import { Loader2, Mail, RefreshCw } from "lucide-react";
import { useOutlookSync } from "@/hooks/email";

export function OutlookSyncSection() {
  const { outlookStatus, syncMutation } = useOutlookSync();

  return (
    <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-[#00d4aa]" />
          <h2 className="text-lg font-semibold text-[#e8eaed]">
            Outlook-Integration
          </h2>
        </div>
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          className="flex items-center gap-2 rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-1.5 text-sm text-[#e8eaed] hover:bg-[#2a3040] disabled:opacity-50"
        >
          {syncMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Synchronisieren
        </button>
      </div>
      <p className="text-sm text-[#b8bec6]">
        {outlookStatus?.connected
          ? `Verbunden als ${outlookStatus.user_email}`
          : "Nicht verbunden. Bitte in den Einstellungen Outlook verknüpfen."}
      </p>
    </div>
  );
}
