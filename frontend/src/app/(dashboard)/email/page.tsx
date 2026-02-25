"use client";

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi, emailsApi, LeadListItem } from "@/lib/api";
import { Loader2, AlertCircle, Mail, Send, RefreshCw, CheckCircle, ExternalLink, XCircle, Plus, Pencil, Trash2, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmailTemplateItem {
  id: number;
  name: string;
  betreff: string;
  inhalt: string;
  kategorie?: string;
  is_ab_test: boolean;
  version: number;
  variables?: Record<string, unknown>;
  created_at: string;
}

interface SequenceStepItem {
  day_offset: number;
  template_id?: number;
  subject_override?: string;
  body_override?: string;
}

interface SequenceStepPreviewItem {
  stepIndex: number;
  dayOffset: number;
  templateName: string;
  subject: string;
  plain: string;
}

interface SequenceScheduleItem {
  stepIndex: number;
  dayOffset: number;
  effectiveOffset: number;
  scheduledDateLabel: string;
  templateName: string;
}

interface SequenceTimelineExport {
  exported_at: string;
  sequence_id: number | null;
  sequence_name: string;
  sequence_beschreibung: string;
  schedule_mode: "from-start" | "cumulative";
  start_date: string;
  steps: SequenceStepItem[];
  timeline: SequenceScheduleItem[];
}

export default function EmailPage() {
  const queryClient = useQueryClient();
  const [selectedLead, setSelectedLead] = useState<string>("");
  const [generatedEmail, setGeneratedEmail] = useState<{ subject: string; body: string } | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [editingTemplateId, setEditingTemplateId] = useState<number | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateBetreff, setTemplateBetreff] = useState("");
  const [templateInhalt, setTemplateInhalt] = useState("");
  const [templateKategorie, setTemplateKategorie] = useState("");
  const [composerLeadId, setComposerLeadId] = useState<string>("");
  const [composerTemplateId, setComposerTemplateId] = useState<string>("");
  const [leadSearch, setLeadSearch] = useState("");
  const [previewType, setPreviewType] = useState<"desktop" | "mobile" | "plain">("desktop");
  const [composerSubject, setComposerSubject] = useState("");
  const [composerBody, setComposerBody] = useState("");
  const [activeField, setActiveField] = useState<"subject" | "body">("body");
  const [sequenceName, setSequenceName] = useState("");
  const [sequenceBeschreibung, setSequenceBeschreibung] = useState("");
  const [sequenceSteps, setSequenceSteps] = useState<SequenceStepItem[]>([{ day_offset: 0 }]);
  const [selectedSequenceId, setSelectedSequenceId] = useState<string>("");
  const [sequenceLeadIds, setSequenceLeadIds] = useState<number[]>([]);
  const [sequenceStartNow, setSequenceStartNow] = useState(true);
  const [sequencePreviewLeadId, setSequencePreviewLeadId] = useState<string>("");
  const [sequencePreviewItems, setSequencePreviewItems] = useState<SequenceStepPreviewItem[]>([]);
  const [isSequencePreviewLoading, setIsSequencePreviewLoading] = useState(false);
  const [scheduleReferenceDate, setScheduleReferenceDate] = useState<string>(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  });
  const [scheduleMode, setScheduleMode] = useState<"from-start" | "cumulative">("from-start");
  const sequenceImportInputRef = useRef<HTMLInputElement | null>(null);
  const [hasImportedSequenceConfig, setHasImportedSequenceConfig] = useState(false);

  const { data: leadsData } = useQuery({
    queryKey: ["leads-all"],
    queryFn: () => leadsApi.list({ limit: 100 }),
  });

  const leads = leadsData?.leads || [];

  const { data: analytics } = useQuery({
    queryKey: ["email-analytics", 14],
    queryFn: () => emailsApi.getAnalyticsDashboard(14),
    refetchInterval: 60000,
  });

  // Query for Outlook status
  const { data: outlookStatus } = useQuery({
    queryKey: ["outlook-status"],
    queryFn: () => emailsApi.getOutlookStatus(),
    refetchInterval: 30000,
  });

  // Query for synced emails
  const { data: syncedEmails } = useQuery({
    queryKey: ["synced-emails"],
    queryFn: () => emailsApi.getSyncedEmails(50),
  });

  const { data: templatesData } = useQuery({
    queryKey: ["email-templates"],
    queryFn: () => emailsApi.listTemplates(),
  });

  const { data: sequencesData } = useQuery({
    queryKey: ["email-sequences"],
    queryFn: () => emailsApi.listSequences(),
  });

  const { data: sequenceStats } = useQuery({
    queryKey: ["email-sequence-stats", selectedSequenceId],
    queryFn: () => emailsApi.getSequenceStats(Number(selectedSequenceId)),
    enabled: Boolean(selectedSequenceId),
  });

  const { data: sequenceLeads } = useQuery({
    queryKey: ["email-sequence-leads", selectedSequenceId],
    queryFn: () => emailsApi.getSequenceLeads(Number(selectedSequenceId)),
    enabled: Boolean(selectedSequenceId),
  });

  const { data: composerPreview, isFetching: isPreviewLoading, refetch: refetchPreview } = useQuery({
    queryKey: ["email-preview", composerLeadId, composerTemplateId, previewType],
    queryFn: () => emailsApi.preview({
      lead_id: Number(composerLeadId),
      template_id: Number(composerTemplateId),
      preview_type: previewType,
    }),
    enabled: Boolean(composerLeadId && composerTemplateId),
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

  const createTemplateMutation = useMutation({
    mutationFn: () => emailsApi.createTemplate({
      name: templateName,
      betreff: templateBetreff,
      inhalt: templateInhalt,
      kategorie: templateKategorie || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setTemplateName("");
      setTemplateBetreff("");
      setTemplateInhalt("");
      setTemplateKategorie("");
      setToast({ message: "Template erstellt", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Template-Fehler: ${error.message}`, type: "error" });
    },
  });

  const updateTemplateMutation = useMutation({
    mutationFn: (id: number) => emailsApi.updateTemplate(id, {
      name: templateName,
      betreff: templateBetreff,
      inhalt: templateInhalt,
      kategorie: templateKategorie || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setEditingTemplateId(null);
      setTemplateName("");
      setTemplateBetreff("");
      setTemplateInhalt("");
      setTemplateKategorie("");
      setToast({ message: "Template aktualisiert", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Update-Fehler: ${error.message}`, type: "error" });
    },
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: (id: number) => emailsApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setToast({ message: "Template gelöscht", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Löschen fehlgeschlagen: ${error.message}`, type: "error" });
    },
  });

  const duplicateTemplateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => emailsApi.duplicateTemplate(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setToast({ message: "Template dupliziert", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Duplizieren fehlgeschlagen: ${error.message}`, type: "error" });
    },
  });

  const createSequenceMutation = useMutation({
    mutationFn: () =>
      emailsApi.createSequence({
        name: sequenceName.trim(),
        beschreibung: sequenceBeschreibung.trim() || undefined,
        steps: sequenceSteps,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["email-sequences"] });
      setSelectedSequenceId(String(data.id));
      setSequenceName("");
      setSequenceBeschreibung("");
      setSequenceSteps([{ day_offset: 0 }]);
      setHasImportedSequenceConfig(false);
      setToast({ message: "Sequence erstellt", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Sequence-Fehler: ${error.message}`, type: "error" });
    },
  });

  const updateSequenceMutation = useMutation({
    mutationFn: () =>
      emailsApi.updateSequence(Number(selectedSequenceId), {
        name: sequenceName.trim() || undefined,
        beschreibung: sequenceBeschreibung.trim() || undefined,
        steps: sequenceSteps,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-sequences"] });
      setToast({ message: "Sequence aktualisiert", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Update fehlgeschlagen: ${error.message}`, type: "error" });
    },
  });

  const assignSequenceMutation = useMutation({
    mutationFn: () =>
      emailsApi.assignLeadsToSequence(
        Number(selectedSequenceId),
        sequenceLeadIds,
        sequenceStartNow,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-sequence-stats", selectedSequenceId] });
      queryClient.invalidateQueries({ queryKey: ["email-sequence-leads", selectedSequenceId] });
      setSequenceLeadIds([]);
      setToast({ message: "Leads zur Sequence zugewiesen", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Zuweisung fehlgeschlagen: ${error.message}`, type: "error" });
    },
  });

  const saveImportedSequenceMutation = useMutation({
    mutationFn: () =>
      emailsApi.createSequence({
        name: sequenceName.trim(),
        beschreibung: sequenceBeschreibung.trim() || undefined,
        steps: sequenceSteps,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["email-sequences"] });
      setSelectedSequenceId(String(data.id));
      setHasImportedSequenceConfig(false);
      setToast({ message: "Import als neue Sequence gespeichert", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Import-Speichern fehlgeschlagen: ${error.message}`, type: "error" });
    },
  });

  const leadsWithEmail = leads.filter((l: LeadListItem) => Boolean(l.email));
  const templates = useMemo(() => templatesData || [], [templatesData]);
  const sequences = useMemo(() => sequencesData || [], [sequencesData]);
  const filteredLeads = useMemo(() => {
    const search = leadSearch.trim().toLowerCase();
    if (!search) {
      return leadsWithEmail;
    }
    return leadsWithEmail.filter((lead) => {
      const firma = (lead.firma || "").toLowerCase();
      const email = (lead.email || "").toLowerCase();
      return firma.includes(search) || email.includes(search);
    });
  }, [leadSearch, leadsWithEmail]);

  const sequenceScheduleTimeline = useMemo<SequenceScheduleItem[]>(() => {
    const baseDate = new Date(`${scheduleReferenceDate}T09:00:00`);
    if (Number.isNaN(baseDate.getTime())) {
      return [];
    }

    let cumulativeOffset = 0;

    return sequenceSteps.map((step, index) => {
      const scheduledDate = new Date(baseDate);
      const normalizedOffset = Math.max(0, Number(step.day_offset || 0));
      const effectiveOffset =
        scheduleMode === "cumulative"
          ? (cumulativeOffset += normalizedOffset)
          : normalizedOffset;

      scheduledDate.setDate(baseDate.getDate() + effectiveOffset);

      const templateName =
        templates.find((template) => template.id === step.template_id)?.name || "Custom/Ohne Template";

      return {
        stepIndex: index + 1,
        dayOffset: normalizedOffset,
        effectiveOffset,
        scheduledDateLabel: scheduledDate.toLocaleDateString("de-CH", {
          weekday: "short",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        }),
        templateName,
      };
    });
  }, [scheduleReferenceDate, scheduleMode, sequenceSteps, templates]);

  const toggleSequenceLead = (leadId: number) => {
    setSequenceLeadIds((prev) =>
      prev.includes(leadId)
        ? prev.filter((id) => id !== leadId)
        : [...prev, leadId],
    );
  };

  const submitSequence = () => {
    if (!sequenceName.trim()) {
      setToast({ message: "Bitte Sequence-Namen eingeben", type: "error" });
      return;
    }
    if (sequenceSteps.length === 0) {
      setToast({ message: "Bitte mindestens einen Step hinzufügen", type: "error" });
      return;
    }
    createSequenceMutation.mutate();
  };

  const saveImportedAsNewSequence = () => {
    if (!hasImportedSequenceConfig) {
      setToast({ message: "Bitte zuerst eine JSON-Konfiguration importieren", type: "error" });
      return;
    }
    if (!sequenceName.trim() || sequenceSteps.length === 0) {
      setToast({ message: "Importierte Sequence ist unvollständig", type: "error" });
      return;
    }
    saveImportedSequenceMutation.mutate();
  };

  const submitSequenceUpdate = () => {
    if (!selectedSequenceId) {
      setToast({ message: "Bitte Sequence auswählen", type: "error" });
      return;
    }
    if (sequenceSteps.length === 0) {
      setToast({ message: "Bitte mindestens einen Step hinzufügen", type: "error" });
      return;
    }
    updateSequenceMutation.mutate();
  };

  const addSequenceStep = () => {
    setSequenceSteps((prev) => [...prev, { day_offset: 0 }]);
  };

  const removeSequenceStep = (index: number) => {
    setSequenceSteps((prev) => prev.filter((_, current) => current !== index));
  };

  const updateSequenceStep = (index: number, patch: Partial<SequenceStepItem>) => {
    setSequenceSteps((prev) =>
      prev.map((step, current) =>
        current === index ? { ...step, ...patch } : step,
      ),
    );
  };

  useEffect(() => {
    if (!selectedSequenceId) {
      return;
    }
    const selected = sequences.find((sequence) => sequence.id === Number(selectedSequenceId));
    if (!selected) {
      return;
    }

    setSequenceName(selected.name || "");
    setSequenceBeschreibung(selected.beschreibung || "");
    const normalizedSteps = (selected.steps || []).map((step) => ({
      day_offset: Number(step.day_offset || 0),
      template_id: step.template_id ? Number(step.template_id) : undefined,
      subject_override: step.subject_override || undefined,
      body_override: step.body_override || undefined,
    }));
    setSequenceSteps(normalizedSteps.length > 0 ? normalizedSteps : [{ day_offset: 0 }]);
    setHasImportedSequenceConfig(false);
  }, [selectedSequenceId, sequences]);

  const submitAssignLeads = () => {
    if (!selectedSequenceId) {
      setToast({ message: "Bitte Sequence auswählen", type: "error" });
      return;
    }
    if (sequenceLeadIds.length === 0) {
      setToast({ message: "Bitte mindestens einen Lead auswählen", type: "error" });
      return;
    }
    assignSequenceMutation.mutate();
  };

  const exportSequenceTimelineJson = () => {
    if (!sequenceName.trim() || sequenceSteps.length === 0) {
      setToast({ message: "Bitte zuerst eine gültige Sequence mit Steps anlegen", type: "error" });
      return;
    }

    const exportPayload: SequenceTimelineExport = {
      exported_at: new Date().toISOString(),
      sequence_id: selectedSequenceId ? Number(selectedSequenceId) : null,
      sequence_name: sequenceName,
      sequence_beschreibung: sequenceBeschreibung,
      schedule_mode: scheduleMode,
      start_date: scheduleReferenceDate,
      steps: sequenceSteps,
      timeline: sequenceScheduleTimeline,
    };

    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const safeName = sequenceName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    anchor.href = url;
    anchor.download = `sequence-timeline-${safeName || "export"}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);

    setToast({ message: "Sequence-Timeline als JSON exportiert", type: "success" });
  };

  const triggerSequenceImport = () => {
    sequenceImportInputRef.current?.click();
  };

  const importSequenceTimelineJson = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const content = await file.text();
      const parsed = JSON.parse(content) as Partial<SequenceTimelineExport>;

      if (!parsed.sequence_name || !Array.isArray(parsed.steps)) {
        setToast({ message: "Ungültiges JSON-Format für Sequence-Import", type: "error" });
        return;
      }

      const timelineByStepIndex = new Map<number, string>();
      (parsed.timeline || []).forEach((item) => {
        if (typeof item?.stepIndex === "number" && typeof item?.templateName === "string") {
          timelineByStepIndex.set(item.stepIndex, item.templateName);
        }
      });

      const localTemplatesByName = new Map<string, number>();
      templates.forEach((template) => {
        const key = (template.name || "").trim().toLowerCase();
        if (key) {
          localTemplatesByName.set(key, template.id);
        }
      });

      const unresolvedTemplateNames: string[] = [];
      const normalizedSteps: SequenceStepItem[] = parsed.steps
        .map((step, index) => {
          const originalTemplateId = step.template_id ? Number(step.template_id) : undefined;
          let resolvedTemplateId = originalTemplateId;

          if (resolvedTemplateId && !templates.some((template) => template.id === resolvedTemplateId)) {
            const timelineName = timelineByStepIndex.get(index + 1);
            const normalizedName = (timelineName || "").trim().toLowerCase();
            if (normalizedName && localTemplatesByName.has(normalizedName)) {
              resolvedTemplateId = localTemplatesByName.get(normalizedName);
            } else {
              resolvedTemplateId = undefined;
              if (timelineName && timelineName !== "Custom/Ohne Template") {
                unresolvedTemplateNames.push(timelineName);
              }
            }
          }

          return {
            day_offset: Math.max(0, Number(step.day_offset || 0)),
            template_id: resolvedTemplateId,
            subject_override: step.subject_override || undefined,
            body_override: step.body_override || undefined,
          };
        })
        .filter((step) => Number.isFinite(step.day_offset));

      if (normalizedSteps.length === 0) {
        setToast({ message: "Import enthält keine gültigen Steps", type: "error" });
        return;
      }

      const mode = parsed.schedule_mode === "cumulative" ? "cumulative" : "from-start";
      const hasValidStartDate = typeof parsed.start_date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(parsed.start_date);

      setSequenceName(parsed.sequence_name || "");
      setSequenceBeschreibung(parsed.sequence_beschreibung || "");
      setSequenceSteps(normalizedSteps);
      setScheduleMode(mode);
      if (hasValidStartDate) {
        setScheduleReferenceDate(parsed.start_date as string);
      }
      setSelectedSequenceId("");
      setHasImportedSequenceConfig(true);

      if (unresolvedTemplateNames.length > 0) {
        const uniqueNames = Array.from(new Set(unresolvedTemplateNames));
        setToast({
          message: `Import geladen, aber ohne Mapping für: ${uniqueNames.slice(0, 2).join(", ")}${uniqueNames.length > 2 ? " …" : ""}`,
          type: "error",
        });
      } else {
        setToast({ message: "Sequence-Konfiguration aus JSON geladen", type: "success" });
      }
    } catch {
      setToast({ message: "JSON-Datei konnte nicht gelesen werden", type: "error" });
    } finally {
      event.target.value = "";
    }
  };

  const loadSequencePreview = async () => {
    if (!sequencePreviewLeadId) {
      setToast({ message: "Bitte Lead für Step-Preview auswählen", type: "error" });
      return;
    }
    if (sequenceSteps.length === 0) {
      setToast({ message: "Keine Steps vorhanden", type: "error" });
      return;
    }

    setIsSequencePreviewLoading(true);
    try {
      const previewResults = await Promise.all(
        sequenceSteps.map(async (step, index) => {
          const templateName = templates.find((template) => template.id === step.template_id)?.name || "Custom/Ohne Template";

          if (!step.template_id) {
            return {
              stepIndex: index + 1,
              dayOffset: step.day_offset,
              templateName,
              subject: step.subject_override || "(kein Betreff)",
              plain: step.body_override || "Kein Template gesetzt. Nur Overrides würden gesendet.",
            };
          }

          const preview = await emailsApi.preview({
            lead_id: Number(sequencePreviewLeadId),
            template_id: step.template_id,
            preview_type: "plain",
          });

          return {
            stepIndex: index + 1,
            dayOffset: step.day_offset,
            templateName,
            subject: step.subject_override || preview.subject,
            plain: step.body_override || preview.plain,
          };
        }),
      );

      setSequencePreviewItems(previewResults);
      setToast({ message: "Step-Preview geladen", type: "success" });
    } catch (error) {
      const err = error as Error;
      setToast({ message: `Step-Preview fehlgeschlagen: ${err.message}`, type: "error" });
    } finally {
      setIsSequencePreviewLoading(false);
    }
  };

  const personalizationTags = [
    "{{first_name}}",
    "{{last_name}}",
    "{{company}}",
    "{{domain}}",
    "{{grade}}",
    "{{grade_note}}",
    "{{date}}",
    "{{personalized_greeting}}",
  ];

  const startEditTemplate = (tpl: EmailTemplateItem) => {
    setEditingTemplateId(tpl.id);
    setTemplateName(tpl.name || "");
    setTemplateBetreff(tpl.betreff || "");
    setTemplateInhalt(tpl.inhalt || "");
    setTemplateKategorie(tpl.kategorie || "");
  };

  const resetTemplateForm = () => {
    setEditingTemplateId(null);
    setTemplateName("");
    setTemplateBetreff("");
    setTemplateInhalt("");
    setTemplateKategorie("");
  };

  const submitTemplate = () => {
    if (!templateName.trim() || !templateBetreff.trim() || !templateInhalt.trim()) {
      setToast({ message: "Name, Betreff und Inhalt sind erforderlich", type: "error" });
      return;
    }
    if (editingTemplateId) {
      updateTemplateMutation.mutate(editingTemplateId);
      return;
    }
    createTemplateMutation.mutate();
  };

  const insertTag = (tag: string) => {
    if (activeField === "subject") {
      setComposerSubject((prev) => `${prev}${tag}`);
      return;
    }
    setComposerBody((prev) => `${prev}${tag}`);
  };

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
          <button onClick={() => setToast(null)} title="Hinweis schließen" aria-label="Hinweis schließen" className="ml-2 text-green-400 hover:text-green-200">
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">E-Mail</h1>
        <p className="text-[#b8bec6]">E-Mails generieren und versenden</p>
      </div>

      {/* Visual Composer */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#e8eaed]">Visual Composer</h2>
          <button
            onClick={() => refetchPreview()}
            disabled={!composerLeadId || !composerTemplateId || isPreviewLoading}
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-1.5 text-sm text-[#e8eaed] disabled:opacity-50"
          >
            {isPreviewLoading ? "Lade Vorschau..." : "Vorschau laden"}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <input
              value={leadSearch}
              onChange={(e) => setLeadSearch(e.target.value)}
              placeholder="Lead suchen (Firma oder E-Mail)"
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
            />
            <select
              value={composerLeadId}
              onChange={(e) => setComposerLeadId(e.target.value)}
              aria-label="Lead für Vorschau auswählen"
              title="Lead für Vorschau auswählen"
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
            >
              <option value="">Lead auswählen</option>
              {filteredLeads.map((lead) => (
                <option key={lead.id} value={lead.id}>
                  {lead.firma} - {lead.email}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {templates.map((tpl: EmailTemplateItem) => (
                <button
                  key={tpl.id}
                  onClick={() => {
                    setComposerTemplateId(String(tpl.id));
                    setComposerSubject(tpl.betreff || "");
                    setComposerBody(tpl.inhalt || "");
                  }}
                  className={cn(
                    "rounded-md border px-2 py-1 text-xs",
                    composerTemplateId === String(tpl.id)
                      ? "border-[#00d4aa] text-[#00d4aa]"
                      : "border-[#2a3040] text-[#b8bec6]"
                  )}
                >
                  {tpl.name}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              {(["desktop", "mobile", "plain"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setPreviewType(mode)}
                  className={cn(
                    "rounded-md border px-2 py-1 text-xs capitalize",
                    previewType === mode
                      ? "border-[#00d4aa] text-[#00d4aa]"
                      : "border-[#2a3040] text-[#b8bec6]"
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <input
              value={composerSubject}
              onFocus={() => setActiveField("subject")}
              onChange={(e) => setComposerSubject(e.target.value)}
              placeholder="Subject"
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
            />
            <textarea
              value={composerBody}
              onFocus={() => setActiveField("body")}
              onChange={(e) => setComposerBody(e.target.value)}
              rows={10}
              placeholder="HTML oder Plain Content"
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
            />
            <div className="flex flex-wrap gap-1">
              {personalizationTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => insertTag(tag)}
                  className="rounded border border-[#2a3040] px-2 py-1 text-[11px] text-[#b8bec6] hover:text-[#e8eaed]"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="text-sm font-medium text-[#e8eaed] mb-2">Preview</p>
            <p className="text-xs text-[#b8bec6] mb-2">{composerPreview?.subject || composerSubject || "(kein Betreff)"}</p>
            {previewType === "plain" ? (
              <pre className="whitespace-pre-wrap text-xs text-[#b8bec6] max-h-72 overflow-y-auto">{composerPreview?.plain || composerBody || ""}</pre>
            ) : (
              <div className={cn(
                "rounded border border-[#2a3040] bg-white text-black p-3 max-h-72 overflow-y-auto",
                previewType === "mobile" ? "max-w-[320px]" : "w-full"
              )}>
                <div dangerouslySetInnerHTML={{ __html: composerPreview?.html || composerBody || "" }} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Template Management */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#e8eaed]">Template Management</h2>
          <button
            onClick={resetTemplateForm}
            className="flex items-center gap-2 rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-1.5 text-sm text-[#e8eaed] hover:bg-[#2a3040]"
          >
            <Plus className="h-4 w-4" /> Neues Template
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="Template Name"
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
          />
          <input
            value={templateKategorie}
            onChange={(e) => setTemplateKategorie(e.target.value)}
            placeholder="Kategorie (praxis/kanzlei/followup/custom)"
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
          />
          <input
            value={templateBetreff}
            onChange={(e) => setTemplateBetreff(e.target.value)}
            placeholder="Betreff"
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] md:col-span-2"
          />
          <textarea
            value={templateInhalt}
            onChange={(e) => setTemplateInhalt(e.target.value)}
            placeholder="Template Inhalt"
            rows={5}
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] md:col-span-2"
          />
          <div className="md:col-span-2 flex gap-2">
            <button
              onClick={submitTemplate}
              disabled={createTemplateMutation.isPending || updateTemplateMutation.isPending}
              className="rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
            >
              {editingTemplateId ? "Template speichern" : "Template erstellen"}
            </button>
            {editingTemplateId && (
              <button
                onClick={resetTemplateForm}
                className="rounded-md border border-[#2a3040] px-4 py-2 text-sm text-[#e8eaed]"
              >
                Abbrechen
              </button>
            )}
          </div>
        </div>

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {templates.length > 0 ? (
            templates.map((tpl: EmailTemplateItem) => (
              <div key={tpl.id} className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-[#e8eaed] truncate">{tpl.name}</p>
                    <p className="text-xs text-[#b8bec6] truncate">{tpl.betreff}</p>
                    <p className="text-xs text-[#6b7280] mt-1">v{tpl.version}{tpl.kategorie ? ` · ${tpl.kategorie}` : ""}</p>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => startEditTemplate(tpl)}
                      className="rounded border border-[#2a3040] p-1.5 text-[#b8bec6] hover:text-[#e8eaed]"
                      title="Bearbeiten"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => {
                        const newName = `${tpl.name} (Copy)`;
                        duplicateTemplateMutation.mutate({ id: tpl.id, name: newName });
                      }}
                      className="rounded border border-[#2a3040] p-1.5 text-[#b8bec6] hover:text-[#e8eaed]"
                      title="Duplizieren"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => deleteTemplateMutation.mutate(tpl.id)}
                      className="rounded border border-[#2a3040] p-1.5 text-[#e74c3c] hover:text-[#ff6b5f]"
                      title="Löschen"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-[#6b7280]">Keine Templates vorhanden.</p>
          )}
        </div>
      </div>

      {/* Sequence & Scheduling */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#e8eaed]">Sequence & Scheduling</h2>
          <span className="text-xs text-[#6b7280]">Multi-Step Builder</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            value={sequenceName}
            onChange={(e) => setSequenceName(e.target.value)}
            placeholder="Sequence Name"
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
          />
          <input
            value={sequenceBeschreibung}
            onChange={(e) => setSequenceBeschreibung(e.target.value)}
            placeholder="Beschreibung (optional)"
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
          />
          <div className="md:col-span-2 rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-[#e8eaed]">Steps</p>
              <button
                onClick={addSequenceStep}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#b8bec6]"
              >
                Step hinzufügen
              </button>
            </div>

            <div className="space-y-2">
              {sequenceSteps.map((step, index) => (
                <div key={`${index}-${step.day_offset}-${step.template_id ?? "none"}`} className="grid grid-cols-1 md:grid-cols-4 gap-2 rounded border border-[#2a3040] p-2">
                  <input
                    type="number"
                    min={0}
                    value={step.day_offset}
                    onChange={(e) => updateSequenceStep(index, { day_offset: Number(e.target.value || 0) })}
                    placeholder="Day Offset"
                    aria-label={`Step ${index + 1} Day Offset`}
                    title={`Step ${index + 1} Day Offset`}
                    className="rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                  />
                  <select
                    value={step.template_id ? String(step.template_id) : ""}
                    onChange={(e) => updateSequenceStep(index, { template_id: e.target.value ? Number(e.target.value) : undefined })}
                    aria-label={`Step ${index + 1} Template`}
                    title={`Step ${index + 1} Template`}
                    className="rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                  >
                    <option value="">Template (optional)</option>
                    {templates.map((tpl: EmailTemplateItem) => (
                      <option key={tpl.id} value={tpl.id}>{tpl.name}</option>
                    ))}
                  </select>
                  <input
                    value={step.subject_override || ""}
                    onChange={(e) => updateSequenceStep(index, { subject_override: e.target.value || undefined })}
                    placeholder="Subject Override (optional)"
                    aria-label={`Step ${index + 1} Subject Override`}
                    title={`Step ${index + 1} Subject Override`}
                    className="rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                  />
                  <div className="flex gap-2">
                    <input
                      value={step.body_override || ""}
                      onChange={(e) => updateSequenceStep(index, { body_override: e.target.value || undefined })}
                      placeholder="Body Override (optional)"
                      aria-label={`Step ${index + 1} Body Override`}
                      title={`Step ${index + 1} Body Override`}
                      className="flex-1 rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                    />
                    <button
                      onClick={() => removeSequenceStep(index)}
                      disabled={sequenceSteps.length === 1}
                      className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e74c3c] disabled:opacity-50"
                      title={`Step ${index + 1} entfernen`}
                    >
                      Entfernen
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="md:col-span-2 flex gap-2">
            <button
              onClick={submitSequence}
              disabled={createSequenceMutation.isPending}
              className="rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
            >
              {createSequenceMutation.isPending ? "Erstelle..." : "Sequence erstellen"}
            </button>
            <button
              onClick={submitSequenceUpdate}
              disabled={updateSequenceMutation.isPending || !selectedSequenceId}
              className="rounded-md border border-[#2a3040] px-4 py-2 text-sm text-[#e8eaed] disabled:opacity-50"
            >
              {updateSequenceMutation.isPending ? "Speichere..." : "Ausgewählte Sequence speichern"}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
            <p className="text-sm font-medium text-[#e8eaed]">Bestehende Sequences</p>
            <select
              value={selectedSequenceId}
              onChange={(e) => setSelectedSequenceId(e.target.value)}
              aria-label="Bestehende Sequence auswählen"
              title="Bestehende Sequence auswählen"
              className="w-full rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
            >
              <option value="">Sequence auswählen</option>
              {sequences.map((seq) => (
                <option key={seq.id} value={seq.id}>{seq.name} ({seq.status})</option>
              ))}
            </select>
            <div className="text-xs text-[#b8bec6] space-y-1">
              <p>Gesamt: {sequenceStats?.total_assigned ?? 0}</p>
              <p>Aktiv: {sequenceStats?.active ?? 0}</p>
              <p>Abgeschlossen: {sequenceStats?.completed ?? 0}</p>
            </div>
          </div>

          <div className="md:col-span-2 rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-[#e8eaed]">Leads zuweisen</p>
              <label className="flex items-center gap-2 text-xs text-[#b8bec6]">
                <input
                  type="checkbox"
                  checked={sequenceStartNow}
                  onChange={(e) => setSequenceStartNow(e.target.checked)}
                />
                Start now
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSequenceLeadIds(filteredLeads.slice(0, 20).map((lead) => lead.id))}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#b8bec6]"
              >
                Top 20 auswählen
              </button>
              <button
                onClick={() => setSequenceLeadIds([])}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#b8bec6]"
              >
                Auswahl leeren
              </button>
              <button
                onClick={submitAssignLeads}
                disabled={assignSequenceMutation.isPending}
                className="rounded-md bg-[#00d4aa] px-3 py-1 text-xs font-semibold text-[#0e1117] disabled:opacity-50"
              >
                {assignSequenceMutation.isPending ? "Zuweisung..." : `Ausgewählte zuweisen (${sequenceLeadIds.length})`}
              </button>
            </div>

            <div className="max-h-44 overflow-y-auto space-y-1 pr-1">
              {filteredLeads.slice(0, 30).map((lead) => (
                <label key={lead.id} className="flex items-center gap-2 text-xs text-[#b8bec6]">
                  <input
                    type="checkbox"
                    checked={sequenceLeadIds.includes(lead.id)}
                    onChange={() => toggleSequenceLead(lead.id)}
                  />
                  <span className="truncate">{lead.firma} — {lead.email}</span>
                </label>
              ))}
            </div>

            <div className="border-t border-[#2a3040] pt-2">
              <p className="text-xs text-[#6b7280] mb-1">Aktuelle Assignments</p>
              <div className="max-h-24 overflow-y-auto space-y-1">
                {sequenceLeads && sequenceLeads.length > 0 ? (
                  sequenceLeads.slice(0, 10).map((row) => (
                    <div key={row.assignment_id} className="flex items-center justify-between text-xs text-[#b8bec6]">
                      <span className="truncate">{row.firma}</span>
                      <span>{row.status} · Step {row.current_step}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-[#6b7280]">Keine Assignments</p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-[#e8eaed]">Step Preview</p>
            <button
              onClick={loadSequencePreview}
              disabled={isSequencePreviewLoading}
              className="rounded-md border border-[#2a3040] px-3 py-1 text-xs text-[#e8eaed] disabled:opacity-50"
            >
              {isSequencePreviewLoading ? "Lade..." : "Preview laden"}
            </button>
          </div>

          <select
            value={sequencePreviewLeadId}
            onChange={(e) => setSequencePreviewLeadId(e.target.value)}
            aria-label="Lead für Sequence-Step-Preview auswählen"
            title="Lead für Sequence-Step-Preview auswählen"
            className="w-full rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
          >
            <option value="">Lead für Preview auswählen</option>
            {leadsWithEmail.map((lead: LeadListItem) => (
              <option key={lead.id} value={lead.id}>{lead.firma} - {lead.email}</option>
            ))}
          </select>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {sequencePreviewItems.length > 0 ? (
              sequencePreviewItems.map((item) => (
                <div key={`${item.stepIndex}-${item.dayOffset}-${item.templateName}`} className="rounded border border-[#2a3040] p-2">
                  <div className="flex items-center justify-between text-xs text-[#b8bec6]">
                    <span>Step {item.stepIndex} · Tag {item.dayOffset}</span>
                    <span>{item.templateName}</span>
                  </div>
                  <p className="mt-1 text-xs font-medium text-[#e8eaed]">{item.subject || "(kein Betreff)"}</p>
                  <pre className="mt-1 whitespace-pre-wrap text-[11px] text-[#b8bec6] max-h-24 overflow-y-auto">{item.plain}</pre>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#6b7280]">Noch keine Preview geladen.</p>
            )}
          </div>
        </div>

        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-[#e8eaed]">Scheduler Vorschau</p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#6b7280]">
                {sequenceStartNow ? "Start now aktiv" : "Geplanter Start"}
              </span>
              <button
                onClick={exportSequenceTimelineJson}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e8eaed]"
              >
                JSON Export
              </button>
              <button
                onClick={triggerSequenceImport}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e8eaed]"
              >
                JSON Import
              </button>
              <button
                onClick={saveImportedAsNewSequence}
                disabled={!hasImportedSequenceConfig || saveImportedSequenceMutation.isPending}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e8eaed] disabled:opacity-50"
              >
                {saveImportedSequenceMutation.isPending
                  ? "Speichert..."
                  : "Import als neue Sequence speichern"}
              </button>
              <input
                ref={sequenceImportInputRef}
                type="file"
                accept="application/json,.json"
                onChange={importSequenceTimelineJson}
                aria-label="Sequence JSON importieren"
                title="Sequence JSON importieren"
                className="hidden"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#b8bec6]">Modus</span>
            <button
              onClick={() => setScheduleMode("from-start")}
              className={cn(
                "rounded border px-2 py-1 text-xs",
                scheduleMode === "from-start"
                  ? "border-[#00d4aa] text-[#00d4aa]"
                  : "border-[#2a3040] text-[#b8bec6]",
              )}
            >
              ab Startdatum
            </button>
            <button
              onClick={() => setScheduleMode("cumulative")}
              className={cn(
                "rounded border px-2 py-1 text-xs",
                scheduleMode === "cumulative"
                  ? "border-[#00d4aa] text-[#00d4aa]"
                  : "border-[#2a3040] text-[#b8bec6]",
              )}
            >
              kumulativ
            </button>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-[#b8bec6]" htmlFor="sequence-start-date">
              Startdatum
            </label>
            <input
              id="sequence-start-date"
              type="date"
              value={scheduleReferenceDate}
              onChange={(e) => setScheduleReferenceDate(e.target.value)}
              className="rounded-md border border-[#2a3040] bg-[#111827] px-2 py-1 text-xs text-[#e8eaed]"
            />
          </div>

          <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
            {sequenceScheduleTimeline.length > 0 ? (
              sequenceScheduleTimeline.map((item) => (
                <div key={`${item.stepIndex}-${item.dayOffset}-${item.scheduledDateLabel}`} className="flex items-center justify-between rounded border border-[#2a3040] px-2 py-1 text-xs">
                  <span className="text-[#b8bec6]">Step {item.stepIndex} · +{item.dayOffset} Tage (effektiv +{item.effectiveOffset})</span>
                  <span className="text-[#e8eaed]">{item.scheduledDateLabel} · {item.templateName}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#6b7280]">Bitte gültiges Startdatum setzen.</p>
            )}
          </div>
        </div>
      </div>

      {/* Analytics Dashboard */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#e8eaed]">E-Mail Analytics</h2>
          <span className="text-xs text-[#6b7280]">Letzte 14 Tage</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="text-xs text-[#b8bec6]">Gesendet</p>
            <p className="text-xl font-semibold text-[#e8eaed]">{analytics?.overview.total_sent ?? 0}</p>
          </div>
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="text-xs text-[#b8bec6]">Open Rate</p>
            <p className="text-xl font-semibold text-[#00d4aa]">{analytics?.rates.open_rate ?? 0}%</p>
          </div>
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="text-xs text-[#b8bec6]">Click Rate</p>
            <p className="text-xl font-semibold text-[#3498db]">{analytics?.rates.click_rate ?? 0}%</p>
          </div>
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="text-xs text-[#b8bec6]">Reply Rate</p>
            <p className="text-xl font-semibold text-[#f39c12]">{analytics?.rates.reply_rate ?? 0}%</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="mb-2 text-sm font-medium text-[#e8eaed]">Templates</p>
            <div className="space-y-2">
              {analytics && Object.keys(analytics.by_template).length > 0 ? (
                Object.entries(analytics.by_template).map(([name, value]) => (
                  <div key={name} className="flex items-center justify-between text-sm">
                    <span className="text-[#b8bec6] capitalize">{name}</span>
                    <span className="text-[#e8eaed]">{value.sent} sent · {value.rate}%</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[#6b7280]">Keine Template-Daten</p>
              )}
            </div>
          </div>

          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
            <p className="mb-2 text-sm font-medium text-[#e8eaed]">Timeline</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {analytics?.timeline && analytics.timeline.length > 0 ? (
                analytics.timeline.map((row) => (
                  <div key={row.date} className="flex items-center justify-between text-xs text-[#b8bec6]">
                    <span>{row.date}</span>
                    <span>{row.sent} sent / {row.opened} opened</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-[#6b7280]">Keine Timeline-Daten</p>
              )}
            </div>
          </div>
        </div>
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
          aria-label="Lead auswählen"
          title="Lead auswählen"
          className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          <option value="">-- Lead auswählen --</option>
          {leadsWithEmail.map((lead: LeadListItem) => (
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
            <p className="text-sm">Klicken Sie auf &quot;Synchronisieren&quot; um E-Mails von Outlook abzurufen</p>
          </div>
        )}
      </div>
    </div>
  );
}
