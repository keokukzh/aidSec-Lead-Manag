"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { leadsApi, emailsApi } from "@/lib/api";
import { useMemo } from "react";
import { EmailComposerSection } from "@/components/email/EmailComposerSection";
import { TemplateManagerSection } from "@/components/email/TemplateManagerSection";
import { SequenceBuilderSection } from "@/components/email/SequenceBuilderSection";
import { EmailAnalyticsSection } from "@/components/email/EmailAnalyticsSection";
import { OutlookSyncSection } from "@/components/email/OutlookSyncSection";
import { EmailSendFlowSection } from "@/components/email/EmailSendFlowSection";
import { SyncedEmailsSection } from "@/components/email/SyncedEmailsSection";
import { useOutlookSync } from "@/hooks/email";

export default function EmailPage() {
  const searchParams = useSearchParams();
  const leadParam = searchParams.get("lead");

  const { data: leadsData } = useQuery({
    queryKey: ["leads-all"],
    queryFn: () => leadsApi.list({ limit: 100 }),
  });

  const { data: templatesData } = useQuery({
    queryKey: ["email-templates"],
    queryFn: () => emailsApi.listTemplates(),
  });

  const leads = leadsData?.leads || [];
  const templates = useMemo(() => templatesData || [], [templatesData]);
  const { outlookStatus, syncedEmails, syncMutation } = useOutlookSync();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">E-Mail</h1>
        <p className="text-[#b8bec6]">E-Mails generieren und versenden</p>
      </div>

      <EmailSendFlowSection leads={leads} initialLeadId={leadParam || undefined} />

      <div className="grid gap-6 lg:grid-cols-2">
        <OutlookSyncSection
          outlookStatus={outlookStatus}
          isSyncing={syncMutation.isPending}
          onSync={() => syncMutation.mutate()}
        />
        <SyncedEmailsSection syncedEmails={syncedEmails} />
      </div>

      <EmailComposerSection leads={leads} templates={templates} />

      <TemplateManagerSection templates={templates} />

      <SequenceBuilderSection templates={templates} leads={leads} />

      <EmailAnalyticsSection />
    </div>
  );
}
