"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi, emailsApi } from "@/lib/api";
import { Loader2, AlertCircle, Mail, Send, RefreshCw, CheckCircle, ExternalLink, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function EmailPage() {
  const queryClient = useQueryClient();
  const [selectedLead, setSelectedLead] = useState<string>("");
  const [generatedEmail, setGeneratedEmail] = useState<{ subject: string; body: string } | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const { data: leadsData } = useQuery({
    queryKey: ["leads-all"],
    queryFn: () => leadsApi.list({ limit: 100 }),
  });

  const leads = (leadsData?.leads as any[]) || [];

  // Query for Outlook status
  const { data: outlookStatus } = useQuery({
    queryKey: ["outlook-status"],
    queryFn: () => emailsApi.getOutlookStatus(),
    refetchInterval: 30000,
  });

  // Query for synced emails
  const { data: syncedEmails, refetch: refetchSynced } = useQuery({
    queryKey: ["synced-emails"],
    queryFn: () => emailsApi.getSyncedEmails(50),
  });

  const generateMutation = useMutation({
    mutationFn: (leadId: string) =>
      emailsApi.generate({ lead_id: leadId, stufe: 1 }),
    onSuccess: (data) => {
      setGeneratedEmail(data);
    },
  });

  const sendMutation = useMutation({
    mutationFn: (data: { lead_id: string; subject: string; body: string }) =>
      emailsApi.send(data),
    onSuccess: () => {
      setGeneratedEmail(null);
      setSelectedLead("");
      setToast({ message: "E-Mail erfolgreich gesendet!", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Fehler: ${error.message}`, type: "error" });
    }
  });

  const syncMutation = useMutation({
    mutationFn: () => emailsApi.syncOutlookEmails(50),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["synced-emails"] });
      setToast({
        message: `${data.synced} E-Mails synchronisiert! (${data.matched} zugeordnet)`,
        type: "success"
      });
    },
    onError: (error: Error) => {
      setToast({ message: `Sync-Fehler: ${error.message}`, type: "error" });
    }
  });

  const leadsWithEmail = leads.filter((l: any) => l.email);

  return (
    <div className="space-y-6">
      {toast && (
        <div className={cn(
          "fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg animate-in slide-in-from-bottom-4",
          toast.type === "success" ? "bg-green-900 border border-green-700" : "bg-red-900 border border-red-700"
        )}>
          {toast.type === "success" ? (
            <CheckCircle className="h-5 w-5 text-green-400" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-400" />
          )}
          <span className={cn("text-sm font-medium", toast.type === "success" ? "text-green-200" : "text-red-200")}>
            {toast.message}
          </span>
          <button onClick={() => setToast(null)} className="ml-2 text-green-400 hover:text-green-200">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">E-Mail</h1>
        <p className="text-[#b8bec6]">E-Mails generieren und versenden</p>
      </div>

      {/* Outlook Status & Sync */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mail className="h-5 w-5 text-[#00d4aa]" />
            <div>
              <h2 className="text-lg font-semibold text-[#e8eaed]">Outlook-Integration</h2>
              <p className="text-sm text-[#b8bec6]">
                {outlookStatus?.connected ? (
                  <span className="text-green-400">Verbunden als {outlookStatus.user_email}</span>
                ) : (
                  <span className="text-yellow-400">Nicht verbunden</span>
                )}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending || !outlookStatus?.connected}
              className="flex items-center gap-2 rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-sm text-[#e8eaed] hover:bg-[#2a3040] disabled:opacity-50"
            >
              {syncMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Synchronisieren
            </button>
            <a
              href="/settings"
              className="flex items-center gap-2 rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-sm text-[#e8eaed] hover:bg-[#2a3040]"
            >
              <ExternalLink className="h-4 w-4" />
              Einstellungen
            </a>
          </div>
        </div>
      </div>

      {/* Lead Selection */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">
          Lead auswählen
        </h2>
        <select
          value={selectedLead}
          onChange={(e) => {
            setSelectedLead(e.target.value);
            setGeneratedEmail(null);
          }}
          className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          <option value="">-- Lead auswählen --</option>
          {leadsWithEmail.map((lead: any) => (
            <option key={lead.id} value={lead.id}>
              {lead.firma} - {lead.email}
            </option>
          ))}
        </select>
      </div>

      {/* Generate Button */}
      {selectedLead && !generatedEmail && (
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
          <button
            onClick={() => generateMutation.mutate(selectedLead)}
            disabled={generateMutation.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-[#00d4aa] px-4 py-3 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {generateMutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Generiere...
              </>
            ) : (
              <>
                <RefreshCw className="h-5 w-5" />
                E-Mail generieren (KI)
              </>
            )}
          </button>
        </div>
      )}

      {/* Generated Email */}
      {generatedEmail && (
        <div className="space-y-4">
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">
              Generierte E-Mail
            </h2>

            <div className="mb-4">
              <label className="block text-sm text-[#b8bec6]">Betreff</label>
              <input
                type="text"
                value={generatedEmail.subject}
                onChange={(e) =>
                  setGeneratedEmail({ ...generatedEmail, subject: e.target.value })
                }
                className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm text-[#b8bec6]">Inhalt</label>
              <textarea
                value={generatedEmail.body}
                onChange={(e) =>
                  setGeneratedEmail({ ...generatedEmail, body: e.target.value })
                }
                rows={12}
                className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none font-mono text-sm"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() =>
                sendMutation.mutate({
                  lead_id: selectedLead,
                  subject: generatedEmail.subject,
                  body: generatedEmail.body,
                })
              }
              disabled={sendMutation.isPending}
              className="flex flex-1 items-center justify-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
            >
              {sendMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              E-Mail senden
            </button>
            <button
              onClick={() => setGeneratedEmail(null)}
              className="rounded-md border border-[#2a3040] px-4 py-2 text-[#e8eaed] hover:bg-[#2a3040]"
            >
              Verwerfen
            </button>
          </div>
        </div>
      )}

      {/* Synced Emails */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#e8eaed]">
            Synchronisierte E-Mails
          </h2>
          <span className="text-sm text-[#b8bec6]">
            {syncedEmails?.total || 0} E-Mails
          </span>
        </div>

        {syncedEmails?.emails && syncedEmails.emails.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {syncedEmails.emails.map((email: any) => (
              <div
                key={email.id}
                className="flex items-center justify-between rounded-lg border border-[#2a3040] bg-[#0e1117] p-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[#e8eaed] truncate">
                      {email.firma}
                    </span>
                    <span className="text-xs text-[#6b7280]">
                      {email.lead_email}
                    </span>
                  </div>
                  <div className="text-sm text-[#b8bec6] truncate">
                    {email.betreff}
                  </div>
                </div>
                <div className="ml-4 text-right">
                  <div className="text-xs text-[#6b7280]">
                    {email.gesendet_at ? new Date(email.gesendet_at).toLocaleDateString("de-CH") : "—"}
                  </div>
                  <div className="text-xs text-green-400">
                    Gesendet
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-[#6b7280]">
            <Mail className="mx-auto h-8 w-8 mb-2 opacity-50" />
            <p>Noch keine synchronisierten E-Mails</p>
            <p className="text-sm">Klicken Sie auf "Synchronisieren" um E-Mails von Outlook abzurufen</p>
          </div>
        )}
      </div>
    </div>
  );
}
