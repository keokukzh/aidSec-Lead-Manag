"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import type { EmailTemplateItem } from "./types";

export function useTemplateManager() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editingTemplateId, setEditingTemplateId] = useState<number | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateBetreff, setTemplateBetreff] = useState("");
  const [templateInhalt, setTemplateInhalt] = useState("");
  const [templateKategorie, setTemplateKategorie] = useState("");

  const createTemplateMutation = useMutation({
    mutationFn: () =>
      emailsApi.createTemplate({
        name: templateName,
        betreff: templateBetreff,
        inhalt: templateInhalt,
        kategorie: templateKategorie || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      resetForm();
      showToast({ message: "Template erstellt", type: "success" });
    },
    onError: (error: Error) => {
      showToast({ message: `Template-Fehler: ${error.message}`, type: "error" });
    },
  });

  const updateTemplateMutation = useMutation({
    mutationFn: (id: number) =>
      emailsApi.updateTemplate(id, {
        name: templateName,
        betreff: templateBetreff,
        inhalt: templateInhalt,
        kategorie: templateKategorie || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setEditingTemplateId(null);
      resetForm();
      showToast({ message: "Template aktualisiert", type: "success" });
    },
    onError: (error: Error) => {
      showToast({ message: `Update-Fehler: ${error.message}`, type: "error" });
    },
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: (id: number) => emailsApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      showToast({ message: "Template gelöscht", type: "success" });
    },
    onError: (error: Error) => {
      showToast({
        message: `Löschen fehlgeschlagen: ${error.message}`,
        type: "error",
      });
    },
  });

  const duplicateTemplateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      emailsApi.duplicateTemplate(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      showToast({ message: "Template dupliziert", type: "success" });
    },
    onError: (error: Error) => {
      showToast({
        message: `Duplizieren fehlgeschlagen: ${error.message}`,
        type: "error",
      });
    },
  });

  const resetForm = () => {
    setTemplateName("");
    setTemplateBetreff("");
    setTemplateInhalt("");
    setTemplateKategorie("");
  };

  const startEdit = (tpl: EmailTemplateItem) => {
    setEditingTemplateId(tpl.id);
    setTemplateName(tpl.name || "");
    setTemplateBetreff(tpl.betreff || "");
    setTemplateInhalt(tpl.inhalt || "");
    setTemplateKategorie(tpl.kategorie || "");
  };

  const submitTemplate = () => {
    if (!templateName.trim() || !templateBetreff.trim() || !templateInhalt.trim()) {
      showToast({
        message: "Name, Betreff und Inhalt sind erforderlich",
        type: "error",
      });
      return;
    }
    if (editingTemplateId) {
      updateTemplateMutation.mutate(editingTemplateId);
    } else {
      createTemplateMutation.mutate();
    }
  };

  return {
    editingTemplateId,
    setEditingTemplateId,
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
  };
}
