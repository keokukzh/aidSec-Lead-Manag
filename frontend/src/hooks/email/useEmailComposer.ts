"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";
import type { EmailTemplateItem } from "./types";
import type { LeadListItem } from "@/lib/api";

const PERSONALIZATION_TAGS = [
  "{{first_name}}",
  "{{last_name}}",
  "{{company}}",
  "{{domain}}",
  "{{grade}}",
  "{{grade_note}}",
  "{{date}}",
  "{{personalized_greeting}}",
];

export function useEmailComposer(
  leads: LeadListItem[]
) {
  const [composerLeadId, setComposerLeadId] = useState<string>("");
  const [composerTemplateId, setComposerTemplateId] = useState<string>("");
  const [leadSearch, setLeadSearch] = useState("");
  const [previewType, setPreviewType] = useState<
    "desktop" | "mobile" | "plain"
  >("desktop");
  const [composerSubject, setComposerSubject] = useState("");
  const [composerBody, setComposerBody] = useState("");
  const [activeField, setActiveField] = useState<"subject" | "body">("body");

  const leadsWithEmail = useMemo(
    () => leads.filter((l) => Boolean(l.email)),
    [leads]
  );

  const filteredLeads = useMemo(() => {
    const search = leadSearch.trim().toLowerCase();
    if (!search) return leadsWithEmail;
    return leadsWithEmail.filter((lead) => {
      const firma = (lead.firma || "").toLowerCase();
      const email = (lead.email || "").toLowerCase();
      return firma.includes(search) || email.includes(search);
    });
  }, [leadSearch, leadsWithEmail]);

  const {
    data: composerPreview,
    isFetching: isPreviewLoading,
    refetch: refetchPreview,
  } = useQuery({
    queryKey: ["email-preview", composerLeadId, composerTemplateId, previewType],
    queryFn: () =>
      emailsApi.preview({
        lead_id: Number(composerLeadId),
        template_id: Number(composerTemplateId),
        preview_type: previewType,
      }),
    enabled: Boolean(composerLeadId && composerTemplateId),
  });

  const selectTemplate = (tpl: EmailTemplateItem) => {
    setComposerTemplateId(String(tpl.id));
    setComposerSubject(tpl.betreff || "");
    setComposerBody(tpl.inhalt || "");
  };

  const insertTag = (tag: string) => {
    if (activeField === "subject") {
      setComposerSubject((prev) => `${prev}${tag}`);
    } else {
      setComposerBody((prev) => `${prev}${tag}`);
    }
  };

  return {
    composerLeadId,
    setComposerLeadId,
    composerTemplateId,
    setComposerTemplateId,
    leadSearch,
    setLeadSearch,
    previewType,
    setPreviewType,
    composerSubject,
    setComposerSubject,
    composerBody,
    setComposerBody,
    activeField,
    setActiveField,
    filteredLeads,
    composerPreview,
    isPreviewLoading,
    refetchPreview,
    personalizationTags: PERSONALIZATION_TAGS,
    selectTemplate,
    insertTag,
  };
}
