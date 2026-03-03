"use client";

import { Mail } from "lucide-react";
import type { SyncedEmailsData } from "@/hooks/email/useOutlookSync";

interface SyncedEmailsSectionProps {
  syncedEmails?: SyncedEmailsData;
}

export function SyncedEmailsSection({ syncedEmails }: SyncedEmailsSectionProps) {

  return (
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
          {syncedEmails.emails.map((email) => (
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
                  {email.gesendet_at
                    ? new Date(email.gesendet_at).toLocaleDateString("de-CH")
                    : "—"}
                </div>
                <div className="text-xs text-green-400">Gesendet</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-[#6b7280]">
          <Mail className="mx-auto h-8 w-8 mb-2 opacity-50" />
          <p>Noch keine synchronisierten E-Mails</p>
          <p className="text-sm">
            Klicken Sie auf &quot;Synchronisieren&quot; um E-Mails von Outlook
            abzurufen
          </p>
        </div>
      )}
    </div>
  );
}
