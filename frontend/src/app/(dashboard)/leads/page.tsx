"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { leadsApi } from "@/lib/api";
import { ResearchMissingButton } from "@/components/leads";
import { cn } from "@/lib/utils";
import {
  Search,
  Plus,
  Loader2,
  AlertCircle,
  ChevronRight,
  Trash2,
  RefreshCw,
  Check,
  X,
  Globe,
} from "lucide-react";

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
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [kategorie, setKategorie] = useState("");
  const [stadt, setStadt] = useState("");
  const [ranking, setRanking] = useState("");
  const [quelle, setQuelle] = useState("");
  const [sort, setSort] = useState("newest");

  // Bulk selection
  const [selectedLeads, setSelectedLeads] = useState<Set<number>>(new Set());
  const [bulkAction, setBulkAction] = useState<string>("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["leads", status, kategorie, search, stadt, ranking, quelle, sort],
    queryFn: () =>
      leadsApi.list({
        status: status || undefined,
        kategorie: kategorie || undefined,
        search: search || undefined,
        stadt: stadt || undefined,
        ranking: ranking || undefined,
        quelle: quelle || undefined,
        sort: sort || undefined,
        limit: 200,
      }),
  });

  const leads = data?.leads || [];
  const total = data?.total || 0;

  // Extract unique cities and sources for filters
  const uniqueCities = useMemo(() => {
    const cities = new Set(leads.map((l: any) => l.stadt).filter(Boolean));
    return Array.from(cities).sort();
  }, [leads]);

  const uniqueQuellen = useMemo(() => {
    const quellen = new Set(leads.map((l: any) => l.quelle).filter(Boolean));
    return Array.from(quellen).sort();
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

  const handleSelectAll = () => {
    if (selectedLeads.size === leads.length) {
      setSelectedLeads(new Set());
    } else {
      setSelectedLeads(new Set(leads.map((l: any) => l.id)));
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
      <div className="flex flex-wrap gap-4 rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#b8bec6]" />
          <input
            type="text"
            placeholder="Suche nach Name, Firma, Email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] pl-10 pr-4 py-2 text-[#e8eaed] placeholder-[#6b728099] focus:border-[#00d4aa] focus:outline-none focus:ring-1 focus:ring-[#00d4aa]"
          />
        </div>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
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
              className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-1.5 text-sm text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
            >
              <option value="">Aktion wählen...</option>
              <option value="offen">Status: Offen</option>
              <option value="pending">Status: Pending</option>
              <option value="gewonnen">Status: Gewonnen</option>
              <option value="verloren">Status: Verloren</option>
              <option value="delete" className="text-red-500">
                Löschen
              </option>
            </select>
            <button
              onClick={handleBulkAction}
              disabled={!bulkAction || bulkStatusMutation.isPending || bulkDeleteMutation.isPending}
              className="flex items-center gap-1 rounded-md bg-[#00d4aa] px-3 py-1.5 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
            >
              {bulkStatusMutation.isPending || bulkDeleteMutation.isPending ? (
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
                {leads.map((lead: any, index: number) => (
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
