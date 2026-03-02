"use client";

import { Loader2, Send, RefreshCw } from "lucide-react";
import { useEmailSendFlow } from "@/hooks/email";
import type { LeadListItem } from "@/lib/api";

interface EmailSendFlowSectionProps {
  leads: LeadListItem[];
}

export function EmailSendFlowSection({ leads }: EmailSendFlowSectionProps) {
  const {
    selectedLead,
    setSelectedLead,
    generatedEmail,
    setGeneratedEmail,
    generateMutation,
    sendMutation,
    onLeadChange,
  } = useEmailSendFlow();

  const leadsWithEmail = leads.filter((l) => Boolean(l.email));

  return (
    <>
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">
          Lead auswählen
        </h2>
        <select
          value={selectedLead}
          onChange={(e) => onLeadChange(e.target.value)}
          aria-label="Lead auswählen"
          title="Lead auswählen"
          className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          <option value="">-- Lead auswählen --</option>
          {leadsWithEmail.map((lead) => (
            <option key={lead.id} value={lead.id}>
              {lead.firma} - {lead.email}
            </option>
          ))}
        </select>
      </div>

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
                aria-label="E-Mail-Betreff bearbeiten"
                title="E-Mail-Betreff bearbeiten"
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
                aria-label="E-Mail-Inhalt bearbeiten"
                title="E-Mail-Inhalt bearbeiten"
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
    </>
  );
}
