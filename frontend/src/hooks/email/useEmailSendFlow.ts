"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";
import { useToast } from "@/context/ToastContext";

export function useEmailSendFlow(initialLeadId?: string) {
  const { showToast } = useToast();
  const [selectedLead, setSelectedLead] = useState<string>(initialLeadId ?? "");
  const [generatedEmail, setGeneratedEmail] = useState<{
    subject: string;
    body: string;
  } | null>(null);

  const generateMutation = useMutation({
    mutationFn: (leadId: string) =>
      emailsApi.generate({ lead_id: leadId, stufe: 1 }),
    onSuccess: (data) => {
      setGeneratedEmail(data);
    },
    onError: (error: Error) => {
      showToast({ message: `Generate-Fehler: ${error.message}`, type: "error" });
    },
  });

  const sendMutation = useMutation({
    mutationFn: (data: { lead_id: string; subject: string; body: string }) =>
      emailsApi.send(data),
    onSuccess: () => {
      setGeneratedEmail(null);
      setSelectedLead("");
      showToast({ message: "E-Mail erfolgreich gesendet!", type: "success" });
    },
    onError: (error: Error) => {
      showToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });

  const onLeadChange = (leadId: string) => {
    setSelectedLead(leadId);
    setGeneratedEmail(null);
  };

  return {
    selectedLead,
    setSelectedLead,
    generatedEmail,
    setGeneratedEmail,
    generateMutation,
    sendMutation,
    onLeadChange,
  };
}
