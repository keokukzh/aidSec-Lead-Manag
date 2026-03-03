"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { leadsApi, LeadListItem, emailsApi, followupsApi, agentTasksApi } from "@/lib/api";
import { ResearchMissingButton } from "@/components/leads";
import { cn } from "@/lib/utils";
import {
  Search,
  Plus,
  Loader2,
  AlertCircle,
  ChevronRight,
} from "lucide-react";

type LeadStatus =
  | "offen"
  | "pending"
  | "response_received"
  | "offer_sent"
  | "negotiation"
  | "gewonnen"
  | "verloren";

type PipelineBucket = { items: LeadListItem[]; total: number };
type PipelineResponse = Record<LeadStatus, PipelineBucket>;

const statusOptions = [
  { value: "", label: "Alle Status" },
  { value: "offen", label: "Offen" },
  { value: "pending", label: "Pending" },
  { value: "gewonnen", label: "Gewonnen" },
  { value: "verloren", label: "Verloren" },
];

const kategorieOptions = [
  { value: "", label: "Alle Kategorien" },
  { value: "anwalt", label: "Anwalt" },
  { value: "praxis", label: "Praxis" },
  { value: "wordpress", label: "WordPress" },
];

const rankingOptions = [
  { value: "", label: "Alle Rankings" },
  { value: "A", label: "Ranking A" },
  { value: "B", label: "Ranking B" },
  { value: "C", label: "Ranking C" },
  { value: "none", label: "Nicht gerankt" },
];

const sortOptions = [
  { value: "stale_first", label: "Stale zuerst (Priorität)" },
  { value: "followup_due_first", label: "Fällige Follow-ups zuerst" },
  { value: "newest", label: "Neueste zuerst" },
  { value: "oldest", label: "Älteste zuerst" },
  { value: "firma_asc", label: "Firma A-Z" },
  { value: "firma_desc", label: "Firma Z-A" },
  { value: "ranking_desc", label: "Ranking (beste zuerst)" },
  { value: "ranking_asc", label: "Ranking (schlechteste zuerst)" },
];

function getStatusBadge(status: string) {
  const badges: Record<string, string> = {
    offen: "badge-offen",
    pending: "badge-pending",
    gewonnen: "badge-gewonnen",
    verloren: "badge-verloren",
  };
  return badges[status] || "badge-offen";
}

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("de-CH", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function LeadsPage() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status") || "";
  const initialRanking = searchParams.get("ranking") || "";
  const initialSort = searchParams.get("sort") || "stale_first";
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(initialStatus);
  const [kategorie, setKategorie] = useState("");
  const [stadt, setStadt] = useState("");
  const [ranking, setRanking] = useState(initialRanking);
  const [sort, setSort] = useState(initialSort);

  // Bulk selection
  const [selectedLeads, setSelectedLeads] = useState<Set<number>>(new Set());
  const [bulkAction, setBulkAction] = useState<string>("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["leads", status, kategorie, search, stadt, ranking, sort],
    queryFn: () =>
      leadsApi.list({
        status: status || undefined,
        kategorie: kategorie || undefined,
        search: search || undefined,
        stadt: stadt || undefined,
        ranking: ranking || undefined,
        sort: sort || undefined,
        limit: 200,
      }),
  });

  const leads = useMemo(() => data?.leads || [], [data?.leads]);
  const total = data?.total || 0;

  const { data: pipelineData } = useQuery({
    queryKey: ["pipeline", "queue-overview"],
    queryFn: () => leadsApi.getPipeline(1),
  });

  const { data: draftQueue } = useQuery({
    queryKey: ["drafts", "queue-overview"],
    queryFn: () => emailsApi.listDrafts(),
  });

  const { data: pendingFollowups } = useQuery({
    queryKey: ["followups", "queue-overview", "pending"],
    queryFn: () => followupsApi.list({ due: "pending" }),
  });

  const { data: recentTasks } = useQuery({
    queryKey: ["tasks", "queue-overview"],
    queryFn: () => agentTasksApi.listTasks(200),
  });

  const queues = useMemo(() => {
    const p = (pipelineData || {}) as PipelineResponse;
    const needsQualification = (p.offen?.total || 0) + (p.response_received?.total || 0);
    const readyForOutreach =
      (p.pending?.total || 0) +
      (p.offer_sent?.total || 0) +
      (p.negotiation?.total || 0);
    const draftApproval = draftQueue?.length || 0;
    const replyFollowup = pendingFollowups?.length || 0;
    const blocked =
      recentTasks?.filter((task) => task.status === "failed" || task.status === "error").length || 0;

    return {
      needsQualification,
      readyForOutreach,
      draftApproval,
      replyFollowup,
      blocked,
    };
  }, [pipelineData, draftQueue, pendingFollowups, recentTasks]);

  // Extract unique cities and sources for filters
  const uniqueCities = useMemo(() => {
    const cities = new Set(
      leads
        .map((l: LeadListItem) => l.stadt)
        .filter((city): city is string => Boolean(city))
    );
    return Array.from(cities).sort();
  }, [leads]);

  // Bulk status mutation
  const bulkStatusMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: number[]; status: string }) =>
      leadsApi.bulkStatus(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setSelectedLeads(new Set());
      setBulkAction("");
    },
  });

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => leadsApi.bulkDelete(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setSelectedLeads(new Set());
    },
  });

  // Bulk Security Scan mutation
  const bulkSecurityScanMutation = useMutation({
    mutationFn: (ids: number[]) => leadsApi.bulkSecurityScan(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      setSelectedLeads(new Set());
      setBulkAction("");
      alert("Security-Scan gestartet. Ergebnisse erscheinen in Kürze.");
    },
  });

  const handleSelectAll = () => {
    if (selectedLeads.size === leads.length) {
      setSelectedLeads(new Set());
    } else {
      setSelectedLeads(new Set(leads.map((l: LeadListItem) => l.id)));
    }
  };

  const handleSelectLead = (id: number) => {
    const newSet = new Set(selectedLeads);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedLeads(newSet);
  };

  const handleBulkAction = () => {
    if (!bulkAction || selectedLeads.size === 0) return;

    const ids = Array.from(selectedLeads);

    if (bulkAction === "delete") {
      if (confirm(`${ids.length} Leads wirklich löschen?`)) {
        bulkDeleteMutation.mutate(ids);
      }
    } else if (bulkAction === "security-scan") {
      bulkSecurityScanMutation.mutate(ids);
    } else if (bulkAction === "offen" || bulkAction === "pending" || bulkAction === "gewonnen" || bulkAction === "verloren") {
      bulkStatusMutation.mutate({ ids, status: bulkAction });
    }
    setBulkAction("");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Leads</h1>
          <p className="text-[#b8bec6]">{total} Leads insgesamt</p>
        </div>
        <div className="flex items-center gap-2">
          <ResearchMissingButton />
          <Link
            href="/leads/new"
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] transition-all hover:bg-[#00e8bb]"
          >
            <Plus className="h-5 w-5" />
            Neuer Lead
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
        <button
          onClick={() => {
            setStatus("offen");
            setRanking("none");
          }}
          className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3 text-left hover:border-[#00d4aa]"
        >
          <p className="text-xs uppercase text-[#b8bec6]">Needs Qualification</p>
          <p className="mt-1 text-2xl font-bold text-[#e8eaed]">{queues.needsQualification}</p>
          <p className="mt-1 text-xs text-[#6b7280]">Offen + Antwort eingegangen</p>
        </button>

        <button
          onClick={() => {
            setStatus("pending");
            setRanking("");
          }}
          className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3 text-left hover:border-[#00d4aa]"
        >
          <p className="text-xs uppercase text-[#b8bec6]">Ready for Outreach</p>
          <p className="mt-1 text-2xl font-bold text-[#e8eaed]">{queues.readyForOutreach}</p>
          <p className="mt-1 text-xs text-[#6b7280]">Pending + Angebot + Verhandlung</p>
        </button>

        <Link
          href="/drafts"
          className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3 hover:border-[#00d4aa]"
        >
          <p className="text-xs uppercase text-[#b8bec6]">Draft Approval</p>
          <p className="mt-1 text-2xl font-bold text-[#e8eaed]">{queues.draftApproval}</p>
          <p className="mt-1 text-xs text-[#6b7280]">Manuelle Freigabe erforderlich</p>
        </Link>

        <Link
          href="/followups"
          className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3 hover:border-[#00d4aa]"
        >
          <p className="text-xs uppercase text-[#b8bec6]">Reply / Follow-up</p>
          <p className="mt-1 text-2xl font-bold text-[#e8eaed]">{queues.replyFollowup}</p>
          <p className="mt-1 text-xs text-[#6b7280]">Offene Follow-ups</p>
        </Link>

        <Link
          href="/tasks"
          className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3 hover:border-[#00d4aa]"
        >
          <p className="text-xs uppercase text-[#b8bec6]">Blocked / Error</p>
          <p className="mt-1 text-2xl font-bold text-[#e8eaed]">{queues.blocked}</p>
          <p className="mt-1 text-xs text-[#6b7280]">Fehlgeschlagene Agent-Tasks</p>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-4">
        <div className="relative flex-1 min-w-50">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#b8bec6]" />
          <input
            type="text"
            placeholder="Suche nach Name, Firma, Email..."
            title="Leads durchsuchen"
            aria-label="Leads durchsuchen"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] pl-10 pr-4 py-2 text-[#e8eaed] placeholder-[#6b728099] focus:border-[#00d4aa] focus:outline-none focus:ring-1 focus:ring-[#00d4aa]"
          />
        </div>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          title="Nach Status filtern"
          aria-label="Nach Status filtern"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <select
          value={kategorie}
          onChange={(e) => setKategorie(e.target.value)}
          title="Nach Kategorie filtern"
          aria-label="Nach Kategorie filtern"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          {kategorieOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <select
          value={stadt}
          onChange={(e) => setStadt(e.target.value)}
          title="Nach Stadt filtern"
          aria-label="Nach Stadt filtern"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          <option value="">Alle Städte</option>
          {uniqueCities.map((city: string) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </select>

        <select
          value={ranking}
          onChange={(e) => setRanking(e.target.value)}
          title="Nach Ranking filtern"
          aria-label="Nach Ranking filtern"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          {rankingOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          title="Sortierung auswählen"
          aria-label="Sortierung auswählen"
          className="rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
        >
          {sortOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Bulk Actions Toolbar */}
      {selectedLeads.size > 0 && (
        <div className="flex items-center gap-4 rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-3">
          <span className="text-sm text-[#b8bec6]">
            {selectedLeads.size} ausgewählt
          </span>
          <div className="flex items-center gap-2">
            <select
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value)}
              title="Bulk-Aktion auswählen"
              aria-label="Bulk-Aktion auswählen"
              className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-1.5 text-sm text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
            >
              <option value="">Aktion wählen...</option>
              <option value="offen">Status: Offen</option>
              <option value="pending">Status: Pending</option>
              <option value="gewonnen">Status: Gewonnen</option>
              <option value="verloren">Status: Verloren</option>
              <option value="security-scan" className="text-[#00d4aa]">Security-Scan ausführen</option>
              <option value="delete" className="text-red-500">
                Löschen
              </option>
            </select>
            <button
              onClick={handleBulkAction}
              disabled={!bulkAction || bulkStatusMutation.isPending || bulkDeleteMutation.isPending || bulkSecurityScanMutation.isPending}
              className="flex items-center gap-1 rounded-md bg-[#00d4aa] px-3 py-1.5 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
            >
              {bulkStatusMutation.isPending || bulkDeleteMutation.isPending || bulkSecurityScanMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Ausführen"
              )}
            </button>
          </div>
          <button
            onClick={() => setSelectedLeads(new Set())}
            className="ml-auto text-sm text-[#b8bec6] hover:text-[#e8eaed]"
          >
            Auswahl aufheben
          </button>
        </div>
      )}

      {/* Leads Table */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] overflow-hidden">
        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
          </div>
        ) : error ? (
          <div className="flex h-64 items-center justify-center">
            <div className="text-center">
              <AlertCircle className="mx-auto mb-2 h-8 w-8 text-[#e74c3c]" />
              <p className="text-[#e74c3c]">Fehler beim Laden der Leads</p>
            </div>
          </div>
        ) : leads.length === 0 ? (
          <div className="flex h-64 items-center justify-center">
            <p className="text-[#b8bec6]">Keine Leads gefunden</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-[#2a3040] bg-[#141926]">
                <tr>
                  <th className="px-2 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedLeads.size === leads.length && leads.length > 0}
                      onChange={handleSelectAll}
                      title="Alle Leads auswählen"
                      aria-label="Alle Leads auswählen"
                      className="h-4 w-4 rounded border-[#2a3040] bg-[#0e1117] text-[#00d4aa] focus:ring-[#00d4aa]"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Firma
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Kontakt
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Stadt
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Kat.
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Rank
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Quelle
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Erstellt
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                    Aktionen
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a3040]">
                {leads.map((lead: LeadListItem, index: number) => (
                  <tr
                    key={lead.id}
                    className={cn(
                      "transition-colors hover:bg-[#00d4aa11]",
                      index % 2 === 0 ? "bg-[#1a1f2e]" : "bg-[#1a1f2e80]"
                    )}
                  >
                    <td className="px-2 py-3">
                      <input
                        type="checkbox"
                        checked={selectedLeads.has(lead.id)}
                        onChange={() => handleSelectLead(lead.id)}
                        title={`Lead ${lead.firma || lead.id} auswählen`}
                        aria-label={`Lead ${lead.firma || lead.id} auswählen`}
                        className="h-4 w-4 rounded border-[#2a3040] bg-[#0e1117] text-[#00d4aa] focus:ring-[#00d4aa]"
                      />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="font-medium text-[#e8eaed]">
                        {lead.firma || "—"}
                      </div>
                      {lead.website && (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[#00d4aa] hover:underline"
                        >
                          Website
                        </a>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="text-[#e8eaed]">{lead.name || "—"}</div>
                      <div className="text-sm text-[#b8bec6]">
                        {lead.email || "—"}
                      </div>
                      <div className="text-xs text-[#b8bec6]">
                        {lead.telefon || "—"}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-[#e8eaed]">
                      {lead.stadt || "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className="text-[#e8eaed] capitalize">
                        {lead.kategorie || "—"}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className={cn("badge", getStatusBadge(lead.status))}>
                        {lead.status || "offen"}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {lead.ranking_grade && (
                        <span
                          className={cn(
                            "grade-badge",
                            `grade-${lead.ranking_grade}`
                          )}
                        >
                          {lead.ranking_grade}
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className={cn(
                        "inline-flex items-center justify-center min-w-8 rounded-sm px-1.5 py-0.5 text-xs font-medium border",
                        (lead.lead_score || 0) >= 60 ? "bg-[#00d4aa]/10 text-[#00d4aa] border-[#00d4aa]/20" :
                        (lead.lead_score || 0) >= 30 ? "bg-[#f39c12]/10 text-[#f39c12] border-[#f39c12]/20" :
                        "bg-[#e74c3c]/10 text-[#e74c3c] border-[#e74c3c]/20"
                      )}>
                        {lead.lead_score || 0}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-[#b8bec6]">
                      {lead.quelle || "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-[#b8bec6]">
                      {formatDate(lead.created_at)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      <Link
                        href={`/leads/${lead.id}`}
                        className="inline-flex items-center gap-1 text-sm text-[#00d4aa] hover:underline"
                      >
                        Ansehen
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Summary */}
      {leads.length > 0 && (
        <div className="text-sm text-[#b8bec6]">
          Zeige {leads.length} von {total} Leads
        </div>
      )}
    </div>
  );
}
