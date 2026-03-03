"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";
import { useToast } from "@/context/ToastContext";

export interface OutlookStatusData {
  connected: boolean;
  configured: boolean;
  user_email?: string;
  message: string;
}

export interface SyncedEmailItem {
  id: number;
  lead_id: number;
  firma: string;
  lead_email: string;
  betreff: string;
  inhalt: string;
  status: string;
  gesendet_at: string | null;
  outlook_message_id: string | null;
  campaign_id: number | null;
}

export interface SyncedEmailsData {
  success: boolean;
  emails: SyncedEmailItem[];
  total: number;
}

interface UseOutlookSyncOptions {
  enableSyncedEmails?: boolean;
}

export function useOutlookSync(options: UseOutlookSyncOptions = {}) {
  const { enableSyncedEmails = true } = options;
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: outlookStatus } = useQuery<OutlookStatusData>({
    queryKey: ["outlook-status"],
    queryFn: () => emailsApi.getOutlookStatus(),
    refetchInterval: 30000,
  });

  const { data: syncedEmails } = useQuery<SyncedEmailsData>({
    queryKey: ["synced-emails"],
    queryFn: () => emailsApi.getSyncedEmails(50),
    enabled: enableSyncedEmails,
  });

  const syncMutation = useMutation({
    mutationFn: () => emailsApi.syncOutlookEmails(50),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["synced-emails"] });
      showToast({
        message: `${data.synced} E-Mails synchronisiert! (${data.matched} zugeordnet)`,
        type: "success",
      });
    },
    onError: (error: Error) => {
      showToast({ message: `Sync-Fehler: ${error.message}`, type: "error" });
    },
  });

  return {
    outlookStatus,
    syncedEmails,
    syncMutation,
  };
}
