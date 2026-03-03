"use client";

import DOMPurify from "dompurify";
import { cn } from "@/lib/utils";
import { useEmailComposer } from "@/hooks/email";
import type { LeadListItem } from "@/lib/api";
import type { EmailTemplateItem } from "@/hooks/email";

interface EmailComposerSectionProps {
  leads: LeadListItem[];
  templates: EmailTemplateItem[];
}

export function EmailComposerSection({ leads, templates }: EmailComposerSectionProps) {
  const {
    composerLeadId,
    setComposerLeadId,
    composerTemplateId,
    leadSearch,
    setLeadSearch,
    previewType,
    setPreviewType,
    composerSubject,
    setComposerSubject,
    composerBody,
    setComposerBody,
    setActiveField,
    filteredLeads,
    composerPreview,
    isPreviewLoading,
    refetchPreview,
    personalizationTags,
    selectTemplate,
    insertTag,
  } = useEmailComposer(leads);

  return (
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
            {templates.map((tpl) => (
              <button
                key={tpl.id}
                onClick={() => selectTemplate(tpl)}
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
          <p className="text-xs text-[#b8bec6] mb-2">
            {composerPreview?.subject || composerSubject || "(kein Betreff)"}
          </p>
          {previewType === "plain" ? (
            <pre className="whitespace-pre-wrap text-xs text-[#b8bec6] max-h-72 overflow-y-auto">
              {composerPreview?.plain || composerBody || ""}
            </pre>
          ) : (
            <div
              className={cn(
                "rounded border border-[#2a3040] bg-white text-black p-3 max-h-72 overflow-y-auto",
                previewType === "mobile" ? "max-w-[320px]" : "w-full"
              )}
            >
              <div
                dangerouslySetInnerHTML={{
                  __html:
                    typeof window !== "undefined"
                      ? DOMPurify.sanitize(
                          composerPreview?.html || composerBody || ""
                        )
                      : "",
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
