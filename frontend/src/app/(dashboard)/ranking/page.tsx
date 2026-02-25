"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leadsApi, rankingApi } from "@/lib/api";
import { Loader2, AlertCircle, TrendingUp, RefreshCw, Layers, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import Link from "next/link";

interface Lead {
  id: number;
  firma: string | null;
  website: string | null;
  kategorie: string | null;
  ranking_score: number | null;
  ranking_grade: string | null;
}

export default function RankingPage() {
  const queryClient = useQueryClient();
  const [kategorie, setKategorie] = useState("");
  // Retrieve job ID from localStorage if exists
  const [activeJobId, setActiveJobId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("aidsec_ranking_job");
    }
    return null;
  });

  const { data: data, isLoading, error, refetch } = useQuery({
    queryKey: ["ranking", kategorie],
    queryFn: () => leadsApi.list({
      kategorie: kategorie || undefined,
      limit: 100,
      status: "offen",
      sort: "ranking"
    }),
  });

  const { data: jobStatus } = useQuery({
    queryKey: ["ranking-job", activeJobId],
    queryFn: () => activeJobId ? rankingApi.getBatchStatus(activeJobId) : null,
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" ? 2000 : false;
    }
  });

  const batchMutation = useMutation({
    mutationFn: (ids: number[]) => rankingApi.batch(ids),
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      localStorage.setItem("aidsec_ranking_job", data.job_id);
    }
  });

  const leads = (data?.leads as Lead[]) || [];
  
  const rankedLeads = leads
    .filter((l) => l.ranking_score !== null)
    .sort((a, b) => (b.ranking_score || 0) - (a.ranking_score || 0));

  const missingLeads = leads.filter((l) => l.ranking_score === null && l.website);

  useEffect(() => {
    if (jobStatus?.status === "done") {
      queryClient.invalidateQueries({ queryKey: ["ranking"] });
      // Clear after 5 seconds to keep the success message visible for a bit
      const timer = setTimeout(() => {
        setActiveJobId(null);
        localStorage.removeItem("aidsec_ranking_job");
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [jobStatus?.status, queryClient]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Ranking</h1>
          <p className="text-[#b8bec6]">Lead-Bewertung und Priorisierung</p>
        </div>
        <div className="flex gap-2">
          <select
            value={kategorie}
            title="Kategorie filtern"
            onChange={(e) => setKategorie(e.target.value)}
            className="rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
          >
            <option value="">Alle Kategorien</option>
            <option value="anwalt">Anwalt</option>
            <option value="praxis">Praxis</option>
            <option value="wordpress">WordPress</option>
          </select>
          <button
            onClick={() => refetch()}
            title="Aktualisieren"
            className="flex items-center gap-2 rounded-md border border-[#2a3040] px-3 py-2 text-[#e8eaed] hover:bg-[#2a3040]"
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Batch Ranking Action */}
      {missingLeads.length > 0 && !activeJobId && (
        <div className="rounded-lg border border-[#00d4aa33] bg-[#00d4aa0a] p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Layers className="h-5 w-5 text-[#00d4aa]" />
            <div>
              <p className="font-medium text-[#e8eaed]">{missingLeads.length} Leads ohne Ranking</p>
              <p className="text-sm text-[#b8bec6]">Erweitern Sie Ihre Datenbasis durch eine automatische Analyse.</p>
            </div>
          </div>
          <button
            onClick={() => batchMutation.mutate(missingLeads.map(l => l.id))}
            disabled={batchMutation.isPending}
            className="rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {batchMutation.isPending ? "Starte..." : "Rankings vervollständigen"}
          </button>
        </div>
      )}

      {/* Progress Monitor */}
      {activeJobId && jobStatus && (
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {jobStatus.status === "running" ? (
                <Loader2 className="h-4 w-4 animate-spin text-[#00d4aa]" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-[#00d4aa]" />
              )}
              <span className="font-medium text-[#e8eaed]">
                {jobStatus.status === "running" ? "Ranking-Prozess läuft..." : "Ranking abgeschlossen"}
              </span>
            </div>
            <span className="text-sm text-[#b8bec6]">
              {jobStatus.completed} / {jobStatus.total} verarbeitet
            </span>
          </div>
          <div className="h-2 w-full bg-[#0e1117] rounded-full overflow-hidden">
            <div 
              className="h-full bg-[#00d4aa] transition-all duration-500"
              style={{ width: `${(jobStatus.completed / jobStatus.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
        </div>
      ) : error ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <AlertCircle className="mx-auto mb-2 h-8 w-8 text-[#e74c3c]" />
            <p className="text-[#e74c3c]">Fehler beim Laden</p>
          </div>
        </div>
      ) : rankedLeads.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-[#2a3040] bg-[#1a1f2e]">
          <TrendingUp className="mb-4 h-12 w-12 text-[#b8bec6]" />
          <p className="text-[#b8bec6]">Noch keine Rankings verfügbar</p>
          <p className="mt-1 text-sm text-[#6b728099]">
            Klicken Sie oben auf &quot;Rankings vervollständigen&quot;
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-[#2a3040] bg-[#141926]">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                  #
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                  Firma
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                  Kategorie
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                  Website
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                  Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[#b8bec6]">
                  Grade
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2a3040]">
              {rankedLeads.map((lead, index) => (
                <tr
                  key={lead.id}
                  className={cn(
                    "transition-colors hover:bg-[#00d4aa11]",
                    index % 2 === 0 ? "bg-[#1a1f2e]" : "bg-[#1a1f2e80]"
                  )}
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[#b8bec6]">
                    {index + 1}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <Link
                      href={`/leads/${lead.id}`}
                      className="font-medium text-[#00d4aa] hover:underline"
                    >
                      {lead.firma || "—"}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-[#e8eaed] capitalize">
                    {lead.kategorie || "—"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-[#b8bec6] text-sm">
                    {lead.website ? (
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-[#00d4aa]"
                      >
                        {lead.website.substring(0, 30)}...
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[#e8eaed]">
                    {lead.ranking_score || 0}
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
