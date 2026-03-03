"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import type {
  EmailTemplateItem,
  SequenceStepItem,
  SequenceStepPreviewItem,
  SequenceScheduleItem,
  SequenceTimelineExport,
} from "./types";

interface SequenceItem {
  id: number;
  name: string;
  beschreibung?: string;
  steps: Array<{
    day_offset: number;
    template_id?: number;
    subject_override?: string;
    body_override?: string;
  }>;
}

export function useSequenceBuilder(
  templates: EmailTemplateItem[],
  leads: Array<{ id: number; firma: string | null; email: string | null }>
) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const sequenceImportInputRef = useRef<HTMLInputElement | null>(null);

  const [sequenceName, setSequenceName] = useState("");
  const [sequenceBeschreibung, setSequenceBeschreibung] = useState("");
  const [sequenceSteps, setSequenceSteps] = useState<SequenceStepItem[]>([
    { day_offset: 0 },
  ]);
  const [selectedSequenceId, setSelectedSequenceId] = useState<string>("");
  const [sequenceLeadIds, setSequenceLeadIds] = useState<number[]>([]);
  const [sequenceStartNow, setSequenceStartNow] = useState(true);
  const [sequencePreviewLeadId, setSequencePreviewLeadId] = useState<string>("");
  const [sequencePreviewItems, setSequencePreviewItems] = useState<
    SequenceStepPreviewItem[]
  >([]);
  const [isSequencePreviewLoading, setIsSequencePreviewLoading] =
    useState(false);
  const [scheduleReferenceDate, setScheduleReferenceDate] = useState<string>(
    () => {
      const now = new Date();
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    }
  );
  const [scheduleMode, setScheduleMode] = useState<
    "from-start" | "cumulative"
  >("from-start");
  const [hasImportedSequenceConfig, setHasImportedSequenceConfig] =
    useState(false);
  const [workerUiNow, setWorkerUiNow] = useState<number>(Date.now());

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

  const {
    data: sequenceWorkerHealth,
    refetch: refetchSequenceWorkerHealth,
    isFetching: isFetchingSequenceWorkerHealth,
  } = useQuery({
    queryKey: ["sequence-worker-health"],
    queryFn: () => emailsApi.getSequenceWorkerHealth(),
    refetchInterval: 15000,
  });

  const {
    data: sequenceExecutionDue,
    refetch: refetchSequenceExecutionDue,
    isFetching: isFetchingSequenceExecutionDue,
  } = useQuery({
    queryKey: ["sequence-execution-due-count"],
    queryFn: () => emailsApi.getSequenceExecutionDueCount(),
    refetchInterval: 15000,
  });

  const sequences = useMemo(() => sequencesData || [], [sequencesData]);
  const leadsWithEmail = useMemo(
    () => leads.filter((l) => Boolean(l.email)),
    [leads]
  );

  const sequenceScheduleTimeline = useMemo<SequenceScheduleItem[]>(() => {
    const baseDate = new Date(`${scheduleReferenceDate}T09:00:00`);
    if (Number.isNaN(baseDate.getTime())) return [];
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
        templates.find((t) => t.id === step.template_id)?.name ||
        "Custom/Ohne Template";
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

  const sequenceWorkerStatusUi = useMemo(() => {
    if (!sequenceWorkerHealth?.enabled) {
      return {
        label: "deaktiviert",
        ringClass: "border-[#6b7280]",
        textClass: "text-[#6b7280]",
      };
    }
    if (sequenceWorkerHealth.last_error) {
      return {
        label: "fehler",
        ringClass: "border-[#e74c3c]",
        textClass: "text-[#e74c3c]",
      };
    }
    if (sequenceWorkerHealth.running) {
      return {
        label: "läuft",
        ringClass: "border-[#00d4aa]",
        textClass: "text-[#00d4aa]",
      };
    }
    return {
      label: "wartend",
      ringClass: "border-[#f39c12]",
      textClass: "text-[#f39c12]",
    };
  }, [sequenceWorkerHealth]);

  useEffect(() => {
    const interval = window.setInterval(() => setWorkerUiNow(Date.now()), 10000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!selectedSequenceId) return;
    const selected = sequences.find(
      (s: SequenceItem) => s.id === Number(selectedSequenceId)
    );
    if (!selected) return;
    setSequenceName(selected.name || "");
    setSequenceBeschreibung(selected.beschreibung || "");
    const normalizedSteps = (selected.steps || []).map((step) => ({
      day_offset: Number(step.day_offset || 0),
      template_id: step.template_id ? Number(step.template_id) : undefined,
      subject_override: step.subject_override || undefined,
      body_override: step.body_override || undefined,
    }));
    setSequenceSteps(
      normalizedSteps.length > 0 ? normalizedSteps : [{ day_offset: 0 }]
    );
    setHasImportedSequenceConfig(false);
  }, [selectedSequenceId, sequences]);

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
      showToast({ message: "Sequence erstellt", type: "success" });
    },
    onError: (error: Error) => {
      showToast({ message: `Sequence-Fehler: ${error.message}`, type: "error" });
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
      showToast({ message: "Sequence aktualisiert", type: "success" });
    },
    onError: (error: Error) => {
      showToast({ message: `Update fehlgeschlagen: ${error.message}`, type: "error" });
    },
  });

  const assignSequenceMutation = useMutation({
    mutationFn: () =>
      emailsApi.assignLeadsToSequence(
        Number(selectedSequenceId),
        sequenceLeadIds,
        sequenceStartNow
      ),
    onSuccess: (result) => {
      queryClient.invalidateQueries({
        queryKey: ["email-sequence-stats", selectedSequenceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["email-sequence-leads", selectedSequenceId],
      });
      setSequenceLeadIds([]);
      showToast({
        message: `Leads zugewiesen: ${result.assignment_added}/${result.assignment_requested}`,
        type: "success",
      });

      const skippedTotal =
        (result.skipped_conflicts || 0) +
        (result.skipped_existing || 0) +
        (result.skipped_missing_email || 0);

      if (skippedTotal > 0) {
        showToast({
          message:
            `Übersprungen: ${skippedTotal} ` +
            `(Konflikte: ${result.skipped_conflicts || 0}, ` +
            `bereits aktiv: ${result.skipped_existing || 0}, ` +
            `ohne E-Mail: ${result.skipped_missing_email || 0})`,
          type: "error",
        });
      }
    },
    onError: (error: Error) => {
      showToast({
        message: `Zuweisung fehlgeschlagen: ${error.message}`,
        type: "error",
      });
    },
  });

  const runSequenceExecutionMutation = useMutation({
    mutationFn: (dryRun: boolean) => emailsApi.runSequenceExecution(100, dryRun),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["sequence-worker-health"] });
      queryClient.invalidateQueries({
        queryKey: ["sequence-execution-due-count"],
      });
      if (selectedSequenceId) {
        queryClient.invalidateQueries({
          queryKey: ["email-sequence-stats", selectedSequenceId],
        });
        queryClient.invalidateQueries({
          queryKey: ["email-sequence-leads", selectedSequenceId],
        });
      }
      showToast({
        message: data.dry_run
          ? `Dry-Run: ${data.processed} fällig, ${data.completed} abgeschlossen simuliert`
          : `Worker-Run: ${data.sent} gesendet, ${data.failed} fehlgeschlagen, ${data.completed} abgeschlossen`,
        type: "success",
      });
    },
    onError: (error: Error) => {
      showToast({
        message: `Worker-Ausführung fehlgeschlagen: ${error.message}`,
        type: "error",
      });
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
      showToast({ message: "Import als neue Sequence gespeichert", type: "success" });
    },
    onError: (error: Error) => {
      showToast({
        message: `Import-Speichern fehlgeschlagen: ${error.message}`,
        type: "error",
      });
    },
  });

  const formatRelativeTime = (isoDate?: string | null): string => {
    if (!isoDate) return "unbekannt";
    const ts = new Date(isoDate).getTime();
    if (Number.isNaN(ts)) return "unbekannt";
    const diffSec = Math.max(0, Math.floor((workerUiNow - ts) / 1000));
    if (diffSec < 60) return `vor ${diffSec}s`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `vor ${diffMin}m`;
    return `vor ${Math.floor(diffMin / 60)}h`;
  };

  const refreshSequenceWorkerPanel = async () => {
    await Promise.all([
      refetchSequenceWorkerHealth(),
      refetchSequenceExecutionDue(),
    ]);
  };

  const toggleSequenceLead = (leadId: number) => {
    setSequenceLeadIds((prev) =>
      prev.includes(leadId) ? prev.filter((id) => id !== leadId) : [...prev, leadId]
    );
  };

  const addSequenceStep = () => {
    setSequenceSteps((prev) => [...prev, { day_offset: 0 }]);
  };

  const removeSequenceStep = (index: number) => {
    setSequenceSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const updateSequenceStep = (index: number, patch: Partial<SequenceStepItem>) => {
    setSequenceSteps((prev) =>
      prev.map((step, i) => (i === index ? { ...step, ...patch } : step))
    );
  };

  const submitSequence = () => {
    if (!sequenceName.trim()) {
      showToast({ message: "Bitte Sequence-Namen eingeben", type: "error" });
      return;
    }
    if (sequenceSteps.length === 0) {
      showToast({ message: "Bitte mindestens einen Step hinzufügen", type: "error" });
      return;
    }
    createSequenceMutation.mutate();
  };

  const saveImportedAsNewSequence = () => {
    if (!hasImportedSequenceConfig) {
      showToast({
        message: "Bitte zuerst eine JSON-Konfiguration importieren",
        type: "error",
      });
      return;
    }
    if (!sequenceName.trim() || sequenceSteps.length === 0) {
      showToast({ message: "Importierte Sequence ist unvollständig", type: "error" });
      return;
    }
    saveImportedSequenceMutation.mutate();
  };

  const submitSequenceUpdate = () => {
    if (!selectedSequenceId) {
      showToast({ message: "Bitte Sequence auswählen", type: "error" });
      return;
    }
    if (sequenceSteps.length === 0) {
      showToast({ message: "Bitte mindestens einen Step hinzufügen", type: "error" });
      return;
    }
    updateSequenceMutation.mutate();
  };

  const submitAssignLeads = () => {
    if (!selectedSequenceId) {
      showToast({ message: "Bitte Sequence auswählen", type: "error" });
      return;
    }
    if (sequenceLeadIds.length === 0) {
      showToast({ message: "Bitte mindestens einen Lead auswählen", type: "error" });
      return;
    }
    assignSequenceMutation.mutate();
  };

  const exportSequenceTimelineJson = () => {
    if (!sequenceName.trim() || sequenceSteps.length === 0) {
      showToast({
        message: "Bitte zuerst eine gültige Sequence mit Steps anlegen",
        type: "error",
      });
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
    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const safeName = sequenceName
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
    anchor.href = url;
    anchor.download = `sequence-timeline-${safeName || "export"}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    showToast({ message: "Sequence-Timeline als JSON exportiert", type: "success" });
  };

  const triggerSequenceImport = () => {
    sequenceImportInputRef.current?.click();
  };

  const importSequenceTimelineJson = async (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const content = await file.text();
      const parsed = JSON.parse(content) as Partial<SequenceTimelineExport>;
      if (!parsed.sequence_name || !Array.isArray(parsed.steps)) {
        showToast({ message: "Ungültiges JSON-Format für Sequence-Import", type: "error" });
        return;
      }
      const timelineByStepIndex = new Map<number, string>();
      (parsed.timeline || []).forEach((item) => {
        if (typeof item?.stepIndex === "number" && typeof item?.templateName === "string") {
          timelineByStepIndex.set(item.stepIndex, item.templateName);
        }
      });
      const localTemplatesByName = new Map<string, number>();
      templates.forEach((t) => {
        const key = (t.name || "").trim().toLowerCase();
        if (key) localTemplatesByName.set(key, t.id);
      });
      const unresolvedTemplateNames: string[] = [];
      const normalizedSteps: SequenceStepItem[] = parsed.steps
        .map((step, index) => {
          let resolvedTemplateId = step.template_id
            ? Number(step.template_id)
            : undefined;
          if (
            resolvedTemplateId &&
            !templates.some((t) => t.id === resolvedTemplateId)
          ) {
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
        showToast({ message: "Import enthält keine gültigen Steps", type: "error" });
        return;
      }
      const mode =
        parsed.schedule_mode === "cumulative" ? "cumulative" : "from-start";
      const hasValidStartDate =
        typeof parsed.start_date === "string" &&
        /^\d{4}-\d{2}-\d{2}$/.test(parsed.start_date);
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
        showToast({
          message: `Import geladen, aber ohne Mapping für: ${uniqueNames.slice(0, 2).join(", ")}${uniqueNames.length > 2 ? " …" : ""}`,
          type: "error",
        });
      } else {
        showToast({ message: "Sequence-Konfiguration aus JSON geladen", type: "success" });
      }
    } catch {
      showToast({ message: "JSON-Datei konnte nicht gelesen werden", type: "error" });
    } finally {
      event.target.value = "";
    }
  };

  const loadSequencePreview = async () => {
    if (!sequencePreviewLeadId) {
      showToast({ message: "Bitte Lead für Step-Preview auswählen", type: "error" });
      return;
    }
    if (sequenceSteps.length === 0) {
      showToast({ message: "Keine Steps vorhanden", type: "error" });
      return;
    }
    setIsSequencePreviewLoading(true);
    try {
      const previewResults = await Promise.all(
        sequenceSteps.map(async (step, index) => {
          const templateName =
            templates.find((t) => t.id === step.template_id)?.name ||
            "Custom/Ohne Template";
          if (!step.template_id) {
            return {
              stepIndex: index + 1,
              dayOffset: step.day_offset,
              templateName,
              subject: step.subject_override || "(kein Betreff)",
              plain:
                step.body_override ||
                "Kein Template gesetzt. Nur Overrides würden gesendet.",
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
        })
      );
      setSequencePreviewItems(previewResults);
      showToast({ message: "Step-Preview geladen", type: "success" });
    } catch (error) {
      showToast({
        message: `Step-Preview fehlgeschlagen: ${(error as Error).message}`,
        type: "error",
      });
    } finally {
      setIsSequencePreviewLoading(false);
    }
  };

  return {
    sequenceName,
    setSequenceName,
    sequenceBeschreibung,
    setSequenceBeschreibung,
    sequenceSteps,
    setSequenceSteps,
    selectedSequenceId,
    setSelectedSequenceId,
    sequenceLeadIds,
    sequenceStartNow,
    setSequenceStartNow,
    sequencePreviewLeadId,
    setSequencePreviewLeadId,
    sequencePreviewItems,
    isSequencePreviewLoading,
    scheduleReferenceDate,
    setScheduleReferenceDate,
    scheduleMode,
    setScheduleMode,
    hasImportedSequenceConfig,
    sequenceImportInputRef,
    sequences,
    sequenceStats,
    sequenceLeads,
    sequenceWorkerHealth,
    sequenceExecutionDue,
    sequenceScheduleTimeline,
    sequenceWorkerStatusUi,
    refetchSequenceWorkerHealth,
    refetchSequenceExecutionDue,
    isFetchingSequenceWorkerHealth,
    isFetchingSequenceExecutionDue,
    createSequenceMutation,
    updateSequenceMutation,
    assignSequenceMutation,
    runSequenceExecutionMutation,
    saveImportedSequenceMutation,
    formatRelativeTime,
    refreshSequenceWorkerPanel,
    toggleSequenceLead,
    addSequenceStep,
    removeSequenceStep,
    updateSequenceStep,
    submitSequence,
    saveImportedAsNewSequence,
    submitSequenceUpdate,
    submitAssignLeads,
    exportSequenceTimelineJson,
    triggerSequenceImport,
    importSequenceTimelineJson,
    loadSequencePreview,
    leadsWithEmail,
    setSequenceLeadIds,
  };
}
