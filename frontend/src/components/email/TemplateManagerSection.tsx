"use client";

import { Plus, Pencil, Trash2, Copy } from "lucide-react";
import { useTemplateManager } from "@/hooks/email";
import type { EmailTemplateItem } from "@/hooks/email";

interface TemplateManagerSectionProps {
  templates: EmailTemplateItem[];
}

export function TemplateManagerSection({ templates }: TemplateManagerSectionProps) {
  const {
    editingTemplateId,
    templateName,
    setTemplateName,
    templateBetreff,
    setTemplateBetreff,
    templateInhalt,
    setTemplateInhalt,
    templateKategorie,
    setTemplateKategorie,
    createTemplateMutation,
    updateTemplateMutation,
    deleteTemplateMutation,
    duplicateTemplateMutation,
    resetForm,
    startEdit,
    submitTemplate,
  } = useTemplateManager();

  return (
    <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#e8eaed]">Template Management</h2>
        <button
          onClick={resetForm}
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
            disabled={
              createTemplateMutation.isPending || updateTemplateMutation.isPending
            }
            className="rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
          >
            {editingTemplateId ? "Template speichern" : "Template erstellen"}
          </button>
          {editingTemplateId && (
            <button
              onClick={resetForm}
              className="rounded-md border border-[#2a3040] px-4 py-2 text-sm text-[#e8eaed]"
            >
              Abbrechen
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {templates.length > 0 ? (
          templates.map((tpl) => (
            <div
              key={tpl.id}
              className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-[#e8eaed] truncate">
                    {tpl.name}
                  </p>
                  <p className="text-xs text-[#b8bec6] truncate">
                    {tpl.betreff}
                  </p>
                  <p className="text-xs text-[#6b7280] mt-1">
                    v{tpl.version}
                    {tpl.kategorie ? ` · ${tpl.kategorie}` : ""}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => startEdit(tpl)}
                    className="rounded border border-[#2a3040] p-1.5 text-[#b8bec6] hover:text-[#e8eaed]"
                    title="Bearbeiten"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      duplicateTemplateMutation.mutate({
                        id: tpl.id,
                        name: `${tpl.name} (Copy)`,
                      });
                    }}
                    className="rounded border border-[#2a3040] p-1.5 text-[#b8bec6] hover:text-[#e8eaed]"
                    title="Duplizieren"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (
                        window.confirm(
                          `Template "${tpl.name}" wirklich löschen?`
                        )
                      ) {
                        deleteTemplateMutation.mutate(tpl.id);
                      }
                    }}
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
  );
}
