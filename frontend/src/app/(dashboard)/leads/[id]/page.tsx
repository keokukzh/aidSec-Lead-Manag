"use client";

import { use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { leadsApi, emailsApi } from "@/lib/api";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Mail,
  Save,
  Trash2,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function LeadDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<any>({});
  const [outlookLoading, setOutlookLoading] = useState(false);

  const { data: lead, isLoading, error } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => leadsApi.get(id),
  });

  const { data: outlookStatus } = useQuery({
    queryKey: ["outlook-configured"],
    queryFn: () => emailsApi.checkOutlookConfigured(),
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => leadsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead", id] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => leadsApi.delete(id),
    onSuccess: () => {
      router.push("/leads");
    },
  });

  const handleOutlookDraft = async () => {
    if (!lead || !(lead as any).email) return;

    setOutlookLoading(true);
    try {
      const result = await emailsApi.createOutlookDraft({
        lead_id: id,
        subject: `Angebot für ${(lead as any).firma}`,
        body: `<p>Sehr geehrte/r ${(lead as any).name},</p><p>...</p>`,
      });

      if (result.success && result.web_link) {
        window.open(result.web_link, "_blank");
      } else {
        alert(result.error || "Fehler beim Erstellen des Entwurfs");
      }
    } catch (err: any) {
      alert(err.message || "Fehler beim Erstellen des Entwurfs");
    } finally {
      setOutlookLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-2 h-8 w-8 text-[#e74c3c]" />
          <p className="text-[#e74c3c]">Lead nicht gefunden</p>
        </div>
      </div>
    );
  }

  const l = lead as any;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/leads"
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#2a3040] text-[#b8bec6] hover:bg-[#00d4aa22] hover:text-[#00d4aa]"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-[#e8eaed]">
              {l.firma || "Lead-Detail"}
            </h1>
            <p className="text-[#b8bec6]">
              {l.name} · {l.email}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
            className="flex items-center gap-2 rounded-md border border-[#e74c3c] px-4 py-2 text-[#e74c3c] hover:bg-[#e74c3c22]"
          >
            <Trash2 className="h-4 w-4" />
            Löschen
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">
              Lead-Informationen
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm text-[#b8bec6]">Firma</label>
                <input
                  type="text"
                  value={isEditing ? (formData.firma ?? l.firma ?? "") : (l.firma ?? "")}
                  onChange={(e) =>
                    setFormData({ ...formData, firma: e.target.value })
                  }
                  disabled={!isEditing}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-sm text-[#b8bec6]">Name</label>
                <input
                  type="text"
                  value={isEditing ? (formData.name ?? l.name ?? "") : (l.name ?? "")}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  disabled={!isEditing}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-sm text-[#b8bec6]">Email</label>
                <input
                  type="email"
                  value={isEditing ? (formData.email ?? l.email ?? "") : (l.email ?? "")}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  disabled={!isEditing}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-sm text-[#b8bec6]">Telefon</label>
                <input
                  type="tel"
                  value={isEditing ? (formData.telefon ?? l.telefon ?? "") : (l.telefon ?? "")}
                  onChange={(e) =>
                    setFormData({ ...formData, telefon: e.target.value })
                  }
                  disabled={!isEditing}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
                />
              </div>
            </div>
          </div>

          {/* Notes */}
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Notizen</h2>
            <textarea
              value={isEditing ? (formData.notes ?? l.notes ?? "") : (l.notes ?? "")}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              disabled={!isEditing}
              rows={6}
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
              placeholder="Notizen zum Lead..."
            />
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status */}
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Status</h2>
            <select
              value={isEditing ? (formData.status ?? l.status ?? "offen") : (l.status ?? "offen")}
              onChange={(e) =>
                setFormData({ ...formData, status: e.target.value })
              }
              disabled={!isEditing}
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
            >
              <option value="offen">Offen</option>
              <option value="pending">Pending</option>
              <option value="gewonnen">Gewonnen</option>
              <option value="verloren">Verloren</option>
            </select>
          </div>

          {/* Category */}
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Kategorie</h2>
            <select
              value={isEditing ? (formData.kategorie ?? l.kategorie ?? "anwalt") : (l.kategorie ?? "anwalt")}
              onChange={(e) =>
                setFormData({ ...formData, kategorie: e.target.value })
              }
              disabled={!isEditing}
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
            >
              <option value="anwalt">Anwalt</option>
              <option value="praxis">Praxis</option>
              <option value="wordpress">WordPress</option>
            </select>
          </div>

          {/* Ranking */}
          {l.ranking_grade && (
            <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
              <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Ranking</h2>
              <div className="flex items-center gap-3">
                <span className={`grade-badge grade-${l.ranking_grade}`}>
                  {l.ranking_grade}
                </span>
                <span className="text-[#b8bec6]">
                  Score: {l.ranking_score || 0}
                </span>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Aktionen</h2>
            <div className="space-y-2">
              <Link
                href={`/email?lead=${id}`}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb]"
              >
                <Mail className="h-4 w-4" />
                E-Mail senden
              </Link>
              <button
                onClick={handleOutlookDraft}
                disabled={outlookLoading || !(outlookStatus?.configured)}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-md border border-[#2a3040] px-4 py-2 text-[#e8eaed] hover:bg-[#00d4aa22] disabled:opacity-50",
                  outlookStatus?.configured && "border-[#0078d4] text-[#0078d4]"
                )}
              >
                {outlookLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ExternalLink className="h-4 w-4" />
                )}
                In Outlook öffnen
              </button>
              {!outlookStatus?.configured && (
                <p className="text-xs text-[#b8bec6] text-center mt-2">
                  Outlook nicht konfiguriert
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Save/Cancel buttons when editing */}
      {isEditing && (
        <div className="flex justify-end gap-2 rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-4">
          <button
            onClick={() => setIsEditing(false)}
            className="rounded-md border border-[#2a3040] px-4 py-2 text-[#e8eaed] hover:bg-[#2a3040]"
          >
            Abbrechen
          </button>
          <button
            onClick={() => updateMutation.mutate(formData)}
            disabled={updateMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {updateMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Speichern
          </button>
        </div>
      )}

      {!isEditing && (
        <button
          onClick={() => setIsEditing(true)}
          className="flex items-center gap-2 rounded-md border border-[#2a3040] px-4 py-2 text-[#e8eaed] hover:bg-[#00d4aa22]"
        >
          Bearbeiten
        </button>
      )}
    </div>
  );
}
