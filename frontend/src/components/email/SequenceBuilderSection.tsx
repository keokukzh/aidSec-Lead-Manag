"use client";

import { cn } from "@/lib/utils";
import { useSequenceBuilder } from "@/hooks/email";
import type { EmailTemplateItem } from "@/hooks/email";
import type { LeadListItem } from "@/lib/api";

interface SequenceBuilderSectionProps {
  templates: EmailTemplateItem[];
  leads: LeadListItem[];
}

export function SequenceBuilderSection({
  templates,
  leads,
}: SequenceBuilderSectionProps) {
  const seq = useSequenceBuilder(templates, leads);

  return (
    <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#e8eaed]">
          Sequence & Scheduling
        </h2>
        <span className="text-xs text-[#6b7280]">Multi-Step Builder</span>
      </div>

      <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-[#e8eaed]">
                Sequence Worker Status
              </p>
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide",
                  seq.sequenceWorkerStatusUi.ringClass,
                  seq.sequenceWorkerStatusUi.textClass
                )}
              >
                {seq.sequenceWorkerStatusUi.label}
              </span>
            </div>
            <p className="text-xs text-[#b8bec6]">
              {seq.sequenceWorkerHealth?.enabled ? "Aktiviert" : "Deaktiviert"} ·{" "}
              {seq.sequenceWorkerHealth?.running ? "läuft" : "gestoppt"}
              {seq.sequenceWorkerHealth?.last_cycle_at
                ? ` · letzter Lauf: ${new Date(seq.sequenceWorkerHealth.last_cycle_at).toLocaleString("de-CH")}`
                : ""}
            </p>
            <p className="text-xs text-[#6b7280]">
              Fällig: {seq.sequenceExecutionDue?.due_count ?? 0} · Aktive
              Assignments: {seq.sequenceExecutionDue?.active_assignments ?? 0}
            </p>
            <p className="text-xs text-[#6b7280]">
              Zuletzt aktualisiert:{" "}
              {seq.formatRelativeTime(seq.sequenceExecutionDue?.timestamp)}
              {seq.sequenceWorkerHealth?.last_cycle_at
                ? ` · letzter Worker-Lauf: ${seq.formatRelativeTime(seq.sequenceWorkerHealth.last_cycle_at)}`
                : ""}
            </p>
            {seq.sequenceWorkerHealth?.last_error ? (
              <p className="text-xs text-[#e74c3c]">
                Letzter Fehler: {seq.sequenceWorkerHealth.last_error}
              </p>
            ) : null}
          </div>
          <div className="flex gap-2">
            <button
              onClick={seq.refreshSequenceWorkerPanel}
              disabled={
                seq.isFetchingSequenceWorkerHealth ||
                seq.isFetchingSequenceExecutionDue
              }
              className="rounded border border-[#2a3040] px-3 py-1 text-xs text-[#e8eaed] disabled:opacity-50"
            >
              {seq.isFetchingSequenceWorkerHealth ||
              seq.isFetchingSequenceExecutionDue
                ? "Aktualisiert..."
                : "Aktualisieren"}
            </button>
            <button
              onClick={() => seq.runSequenceExecutionMutation.mutate(true)}
              disabled={seq.runSequenceExecutionMutation.isPending}
              className="rounded border border-[#2a3040] px-3 py-1 text-xs text-[#e8eaed] disabled:opacity-50"
            >
              {seq.runSequenceExecutionMutation.isPending
                ? "Läuft..."
                : "Dry Run"}
            </button>
            <button
              onClick={() => seq.runSequenceExecutionMutation.mutate(false)}
              disabled={seq.runSequenceExecutionMutation.isPending}
              className="rounded-md bg-[#00d4aa] px-3 py-1 text-xs font-semibold text-[#0e1117] disabled:opacity-50"
            >
              {seq.runSequenceExecutionMutation.isPending
                ? "Läuft..."
                : "Jetzt ausführen"}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <input
          value={seq.sequenceName}
          onChange={(e) => seq.setSequenceName(e.target.value)}
          placeholder="Sequence Name"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
        />
        <input
          value={seq.sequenceBeschreibung}
          onChange={(e) => seq.setSequenceBeschreibung(e.target.value)}
          placeholder="Beschreibung (optional)"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
        />
        <div className="md:col-span-2 rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-[#e8eaed]">Steps</p>
            <button
              onClick={seq.addSequenceStep}
              className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#b8bec6]"
            >
              Step hinzufügen
            </button>
          </div>

          <div className="space-y-2">
            {seq.sequenceSteps.map((step, index) => (
              <div
                key={`${index}-${step.day_offset}-${step.template_id ?? "none"}`}
                className="grid grid-cols-1 md:grid-cols-4 gap-2 rounded border border-[#2a3040] p-2"
              >
                <input
                  type="number"
                  min={0}
                  value={step.day_offset}
                  onChange={(e) =>
                    seq.updateSequenceStep(index, {
                      day_offset: Number(e.target.value || 0),
                    })
                  }
                  placeholder="Day Offset"
                  className="rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                />
                <select
                  value={step.template_id ? String(step.template_id) : ""}
                  onChange={(e) =>
                    seq.updateSequenceStep(index, {
                      template_id: e.target.value
                        ? Number(e.target.value)
                        : undefined,
                    })
                  }
                  className="rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                >
                  <option value="">Template (optional)</option>
                  {templates.map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>
                      {tpl.name}
                    </option>
                  ))}
                </select>
                <input
                  value={step.subject_override || ""}
                  onChange={(e) =>
                    seq.updateSequenceStep(index, {
                      subject_override: e.target.value || undefined,
                    })
                  }
                  placeholder="Subject Override (optional)"
                  className="rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                />
                <div className="flex gap-2">
                  <input
                    value={step.body_override || ""}
                    onChange={(e) =>
                      seq.updateSequenceStep(index, {
                        body_override: e.target.value || undefined,
                      })
                    }
                    placeholder="Body Override (optional)"
                    className="flex-1 rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
                  />
                  <button
                    onClick={() => seq.removeSequenceStep(index)}
                    disabled={seq.sequenceSteps.length === 1}
                    className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e74c3c] disabled:opacity-50"
                  >
                    Entfernen
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="md:col-span-2 flex gap-2">
            <button
              onClick={seq.submitSequence}
              disabled={seq.createSequenceMutation.isPending}
              className="rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
            >
              {seq.createSequenceMutation.isPending
                ? "Erstelle..."
                : "Sequence erstellen"}
            </button>
            <button
              onClick={seq.submitSequenceUpdate}
              disabled={
                seq.updateSequenceMutation.isPending || !seq.selectedSequenceId
              }
              className="rounded-md border border-[#2a3040] px-4 py-2 text-sm text-[#e8eaed] disabled:opacity-50"
            >
              {seq.updateSequenceMutation.isPending
                ? "Speichere..."
                : "Ausgewählte Sequence speichern"}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
            <p className="text-sm font-medium text-[#e8eaed]">
              Bestehende Sequences
            </p>
            <select
              value={seq.selectedSequenceId}
              onChange={(e) => seq.setSelectedSequenceId(e.target.value)}
              className="w-full rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
            >
              <option value="">Sequence auswählen</option>
              {seq.sequences.map((s: { id: number; name: string; status: string }) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.status})
                </option>
              ))}
            </select>
            <div className="text-xs text-[#b8bec6] space-y-1">
              <p>Gesamt: {seq.sequenceStats?.total_assigned ?? 0}</p>
              <p>Aktiv: {seq.sequenceStats?.active ?? 0}</p>
              <p>Abgeschlossen: {seq.sequenceStats?.completed ?? 0}</p>
            </div>
          </div>

          <div className="md:col-span-2 rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-[#e8eaed]">
                Leads zuweisen
              </p>
              <label className="flex items-center gap-2 text-xs text-[#b8bec6]">
                <input
                  type="checkbox"
                  checked={seq.sequenceStartNow}
                  onChange={(e) => seq.setSequenceStartNow(e.target.checked)}
                />
                Start now
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                onClick={() =>
                  seq.setSequenceLeadIds(
                    seq.leadsWithEmail.slice(0, 20).map((l) => l.id)
                  )
                }
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#b8bec6]"
              >
                Top 20 auswählen
              </button>
              <button
                onClick={() => seq.setSequenceLeadIds([])}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#b8bec6]"
              >
                Auswahl leeren
              </button>
              <button
                onClick={seq.submitAssignLeads}
                disabled={seq.assignSequenceMutation.isPending}
                className="rounded-md bg-[#00d4aa] px-3 py-1 text-xs font-semibold text-[#0e1117] disabled:opacity-50"
              >
                {seq.assignSequenceMutation.isPending
                  ? "Zuweisung..."
                  : `Ausgewählte zuweisen (${seq.sequenceLeadIds.length})`}
              </button>
            </div>

            <div className="max-h-44 overflow-y-auto space-y-1 pr-1">
              {seq.leadsWithEmail.slice(0, 30).map((lead) => (
                <label
                  key={lead.id}
                  className="flex items-center gap-2 text-xs text-[#b8bec6]"
                >
                  <input
                    type="checkbox"
                    checked={seq.sequenceLeadIds.includes(lead.id)}
                    onChange={() => seq.toggleSequenceLead(lead.id)}
                  />
                  <span className="truncate">
                    {lead.firma} — {lead.email}
                  </span>
                </label>
              ))}
            </div>

            <div className="border-t border-[#2a3040] pt-2">
              <p className="text-xs text-[#6b7280] mb-1">
                Aktuelle Assignments
              </p>
              <div className="max-h-24 overflow-y-auto space-y-1">
                {seq.sequenceLeads && seq.sequenceLeads.length > 0 ? (
                  seq.sequenceLeads.slice(0, 10).map((row) => (
                    <div
                      key={row.assignment_id}
                      className="flex items-center justify-between text-xs text-[#b8bec6]"
                    >
                      <span className="truncate">{row.firma}</span>
                      <span>
                        {row.status} · Step {row.current_step}
                      </span>
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
              onClick={seq.loadSequencePreview}
              disabled={seq.isSequencePreviewLoading}
              className="rounded-md border border-[#2a3040] px-3 py-1 text-xs text-[#e8eaed] disabled:opacity-50"
            >
              {seq.isSequencePreviewLoading ? "Lade..." : "Preview laden"}
            </button>
          </div>

          <select
            value={seq.sequencePreviewLeadId}
            onChange={(e) => seq.setSequencePreviewLeadId(e.target.value)}
            className="w-full rounded-md border border-[#2a3040] bg-[#111827] px-3 py-2 text-[#e8eaed]"
          >
            <option value="">Lead für Preview auswählen</option>
            {seq.leadsWithEmail.map((lead) => (
              <option key={lead.id} value={lead.id}>
                {lead.firma} - {lead.email}
              </option>
            ))}
          </select>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {seq.sequencePreviewItems.length > 0 ? (
              seq.sequencePreviewItems.map((item) => (
                <div
                  key={`${item.stepIndex}-${item.dayOffset}-${item.templateName}`}
                  className="rounded border border-[#2a3040] p-2"
                >
                  <div className="flex items-center justify-between text-xs text-[#b8bec6]">
                    <span>
                      Step {item.stepIndex} · Tag {item.dayOffset}
                    </span>
                    <span>{item.templateName}</span>
                  </div>
                  <p className="mt-1 text-xs font-medium text-[#e8eaed]">
                    {item.subject || "(kein Betreff)"}
                  </p>
                  <pre className="mt-1 whitespace-pre-wrap text-[11px] text-[#b8bec6] max-h-24 overflow-y-auto">
                    {item.plain}
                  </pre>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#6b7280]">Noch keine Preview geladen.</p>
            )}
          </div>
        </div>

        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-[#e8eaed]">
              Scheduler Vorschau
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={seq.exportSequenceTimelineJson}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e8eaed]"
              >
                JSON Export
              </button>
              <button
                onClick={seq.triggerSequenceImport}
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e8eaed]"
              >
                JSON Import
              </button>
              <button
                onClick={seq.saveImportedAsNewSequence}
                disabled={
                  !seq.hasImportedSequenceConfig ||
                  seq.saveImportedSequenceMutation.isPending
                }
                className="rounded border border-[#2a3040] px-2 py-1 text-xs text-[#e8eaed] disabled:opacity-50"
              >
                {seq.saveImportedSequenceMutation.isPending
                  ? "Speichert..."
                  : "Import als neue Sequence speichern"}
              </button>
              <input
                ref={seq.sequenceImportInputRef}
                type="file"
                accept="application/json,.json"
                onChange={seq.importSequenceTimelineJson}
                className="hidden"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#b8bec6]">Modus</span>
            <button
              onClick={() => seq.setScheduleMode("from-start")}
              className={cn(
                "rounded border px-2 py-1 text-xs",
                seq.scheduleMode === "from-start"
                  ? "border-[#00d4aa] text-[#00d4aa]"
                  : "border-[#2a3040] text-[#b8bec6]"
              )}
            >
              ab Startdatum
            </button>
            <button
              onClick={() => seq.setScheduleMode("cumulative")}
              className={cn(
                "rounded border px-2 py-1 text-xs",
                seq.scheduleMode === "cumulative"
                  ? "border-[#00d4aa] text-[#00d4aa]"
                  : "border-[#2a3040] text-[#b8bec6]"
              )}
            >
              kumulativ
            </button>
          </div>

          <div className="flex items-center gap-2">
            <label
              className="text-xs text-[#b8bec6]"
              htmlFor="sequence-start-date"
            >
              Startdatum
            </label>
            <input
              id="sequence-start-date"
              type="date"
              value={seq.scheduleReferenceDate}
              onChange={(e) =>
                seq.setScheduleReferenceDate(e.target.value)
              }
              className="rounded-md border border-[#2a3040] bg-[#111827] px-2 py-1 text-xs text-[#e8eaed]"
            />
          </div>

          <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
            {seq.sequenceScheduleTimeline.length > 0 ? (
              seq.sequenceScheduleTimeline.map((item) => (
                <div
                  key={`${item.stepIndex}-${item.dayOffset}-${item.scheduledDateLabel}`}
                  className="flex items-center justify-between rounded border border-[#2a3040] px-2 py-1 text-xs"
                >
                  <span className="text-[#b8bec6]">
                    Step {item.stepIndex} · +{item.dayOffset} Tage (effektiv
                    +{item.effectiveOffset})
                  </span>
                  <span className="text-[#e8eaed]">
                    {item.scheduledDateLabel} · {item.templateName}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#6b7280]">
                Bitte gültiges Startdatum setzen.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
