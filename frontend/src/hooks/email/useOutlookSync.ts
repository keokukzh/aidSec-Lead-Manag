"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";
import { useToast } from "@/context/ToastContext";

export function useOutlookSync() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: outlookStatus } = useQuery({
    queryKey: ["outlook-status"],
    queryFn: () => emailsApi.getOutlookStatus(),
    refetchInterval: 30000,
  });

  const { data: syncedEmails } = useQuery({
    queryKey: ["synced-emails"],
    queryFn: () => emailsApi.getSyncedEmails(50),
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
