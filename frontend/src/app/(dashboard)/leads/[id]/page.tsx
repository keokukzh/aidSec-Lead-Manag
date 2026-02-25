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
  Search,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface Lead {
  id: number;
  firma: string | null;
  name: string | null;
  email: string | null;
  telefon: string | null;
  notes: string | null;
  status: string | null;
  kategorie: string | null;
  ranking_score: number | null;
  ranking_grade: string | null;
  website: string | null;
  wordpress_detected: string | null;
  research_status: string | null;
  research_last: string | null;
}

interface PageProps {
  params: Promise<{ id: string }>;
}

const getHostname = (url: string) => {
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname;
  } catch {
    return url;
  }
};

const getValidHref = (url: string) => {
  return url.startsWith("http") ? url : `https://${url}`;
};

export default function LeadDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<Lead>>({});
  const [outlookLoading, setOutlookLoading] = useState(false);

  const { data: lead, isLoading, error, refetch } = useQuery({
    queryKey: ["lead", id],
    queryFn: () => leadsApi.get(id),
  });

  const researchMutation = useMutation({
    mutationFn: () => leadsApi.research(parseInt(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead", id] });
      alert("Research gestartet/abgeschlossen. Daten werden aktualisiert.");
      refetch();
    },
    onError: (err: Error) => alert("Research fehlgeschlagen: " + err.message)
  });

  const generateEmailMutation = useMutation({
    mutationFn: () => emailsApi.generate({ lead_id: id, stufe: 1 }),
    onSuccess: () => {
      router.push(`/email?lead=${id}`);
    },
    onError: (err: Error) => alert("KI E-Mail fehlgeschlagen: " + err.message)
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
    } catch (err: unknown) {
      const error = err as Error;
      alert(error.message || "Fehler beim Erstellen des Entwurfs");
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

  const l = lead as Lead;

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
            <div className="flex items-center gap-2 text-[#b8bec6]">
              <span>{l.name}</span>
              <span>·</span>
              <span>{l.email}</span>
              {l.website && (
                <>
                  <span>·</span>
                  <a
                    href={getValidHref(l.website)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[#00d4aa] hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    {getHostname(l.website)}
                  </a>
                </>
              )}
            </div>
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
                  title="Firma"
                  placeholder="Firmenname"
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
                  title="Name"
                  placeholder="Vollständiger Name"
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
                  title="Email"
                  placeholder="email@beispiel.ch"
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
                  title="Telefon"
                  placeholder="+41 00 000 00 00"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm text-[#b8bec6]">Website</label>
                <input
                  type="url"
                  value={isEditing ? (formData.website ?? l.website ?? "") : (l.website ?? "")}
                  onChange={(e) =>
                    setFormData({ ...formData, website: e.target.value })
                  }
                  disabled={!isEditing}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none disabled:opacity-50"
                  title="Website"
                  placeholder="https://www.beispiel.ch"
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
              title="Notizen"
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
              title="Status ändern"
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
              title="Kategorie ändern"
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

          {/* Website Analyse */}
          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
            <h2 className="mb-4 text-lg font-semibold text-[#e8eaed]">Website-Analyse</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-[#b8bec6]">CMS:</span>
                <span className="text-[#e8eaed font-medium">
                  {l.wordpress_detected || "Unbekannt"}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-[#b8bec6]">Research-Status:</span>
                <span className={cn(
                  "px-2 py-0.5 rounded text-[10px] uppercase font-bold",
                  l.research_status === "completed" ? "bg-green-500/20 text-green-400" : 
                  l.research_status === "in_progress" ? "bg-blue-500/20 text-blue-400" :
                  "bg-gray-500/20 text-gray-400"
                )}>
                  {l.research_status || "Ausstehend"}
                </span>
              </div>
              {l.research_last && (
                <div className="flex justify-between items-center text-sm">
                  <span className="text-[#b8bec6]">Letzte Prüfung:</span>
                  <span className="text-[#e8eaed] text-[10px]">
                    {new Date(l.research_last).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          </div>

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

              <div className="pt-2 border-t border-[#2a3040] mt-2 space-y-2">
                <button
                  onClick={() => researchMutation.mutate()}
                  disabled={researchMutation.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-[#00d4aa] px-4 py-2 text-[#00d4aa] hover:bg-[#00d4aa11] disabled:opacity-50"
                >
                  {researchMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  Daten-Research Agent
                </button>
                <button
                  onClick={() => generateEmailMutation.mutate()}
                  disabled={generateEmailMutation.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-[#a855f7] px-4 py-2 text-[#a855f7] hover:bg-[#a855f711] disabled:opacity-50"
                >
                  {generateEmailMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  KI E-Mail erstellen
                </button>
              </div>
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
