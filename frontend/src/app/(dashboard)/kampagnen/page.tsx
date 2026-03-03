"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignsApi, leadsApi, LeadListItem } from "@/lib/api";
import { Loader2, AlertCircle, Plus, Target, X } from "lucide-react";

interface Campaign {
  id: number;
  name: string;
  beschreibung?: string;
  stufen?: number;
  status?: string;
}

export default function KampagnenPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCampaign, setNewCampaign] = useState({ name: "", beschreibung: "" });
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  const [selectedLeadIds, setSelectedLeadIds] = useState<number[]>([]);
  const [assignmentSummary, setAssignmentSummary] = useState<{
    added: number;
    skippedConflicts: number;
  } | null>(null);

  const { data: campaigns, isLoading, error } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => campaignsApi.list(),
  });

  const { data: leadsData, isLoading: isLeadsLoading } = useQuery({
    queryKey: ["leads", "campaign-assign"],
    queryFn: () =>
      leadsApi.list({
        status: "offen,pending,response_received,offer_sent,negotiation",
        sort: "stale_first",
        limit: 200,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; beschreibung: string }) => campaignsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setIsModalOpen(false);
      setNewCampaign({ name: "", beschreibung: "" });
    },
  });

  const assignMutation = useMutation({
    mutationFn: ({ campaignId, leadIds }: { campaignId: number; leadIds: number[] }) =>
      campaignsApi.assignLeads(campaignId, leadIds),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setAssignmentSummary({
        added: result.added || 0,
        skippedConflicts: result.skipped_conflicts?.length || 0,
      });
      setSelectedLeadIds([]);
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCampaign.name) return;
    createMutation.mutate(newCampaign);
  };

  const campaignList = (campaigns as Campaign[]) || [];
  const leadsWithEmail = useMemo(
    () => (((leadsData?.leads as LeadListItem[]) || []).filter((l) => Boolean(l.email))),
    [leadsData?.leads]
  );

  const toggleLead = (leadId: number) => {
    setSelectedLeadIds((prev) =>
      prev.includes(leadId) ? prev.filter((id) => id !== leadId) : [...prev, leadId]
    );
  };

  const handleAssign = () => {
    if (!selectedCampaignId || selectedLeadIds.length === 0) return;
    setAssignmentSummary(null);
    assignMutation.mutate({
      campaignId: Number(selectedCampaignId),
      leadIds: selectedLeadIds,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Kampagnen</h1>
          <p className="text-[#b8bec6]">E-Mail-Kampagnen verwalten</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb]"
        >
          <Plus className="h-5 w-5" />
          Neue Kampagne
        </button>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg border border-[#2a3040] bg-[#1a1f2e] overflow-hidden shadow-xl">
            <div className="flex items-center justify-between border-b border-[#2a3040] p-4 text-[#e8eaed]">
              <h2 className="text-lg font-semibold">Neue Kampagne erstellen</h2>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-[#b8bec6] hover:text-[#e8eaed]"
                title="Schließen"
                aria-label="Schließen"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleCreate} className="p-4 space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-[#b8bec6]">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={newCampaign.name}
                  onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                  className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] placeholder-[#6b728099] focus:border-[#00d4aa] focus:outline-none"
                  placeholder="z.B. Sommer-Newsletter"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-[#b8bec6]">
                  Beschreibung
                </label>
                <textarea
                  rows={3}
                  value={newCampaign.beschreibung}
                  onChange={(e) => setNewCampaign({ ...newCampaign, beschreibung: e.target.value })}
                  className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] placeholder-[#6b728099] focus:border-[#00d4aa] focus:outline-none"
                  placeholder="Optionale Beschreibung..."
                />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-md px-4 py-2 text-sm font-semibold text-[#b8bec6] hover:bg-[#2a3040] hover:text-[#e8eaed]"
                >
                  Abbrechen
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || !newCampaign.name}
                  className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
                >
                  {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Speichern
                </button>
              </div>
            </form>
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
      ) : campaignList.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-[#2a3040] bg-[#1a1f2e]">
          <Target className="mb-4 h-12 w-12 text-[#b8bec6]" />
          <p className="text-[#b8bec6]">Noch keine Kampagnen erstellt</p>
          <p className="mt-1 text-sm text-[#6b728099]">
            Erstellen Sie Ihre erste Kampagne
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {campaignList.map((campaign: Campaign) => (
              <div
                key={campaign.id}
                className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 transition-all hover:border-[#00d4aa]"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-[#e8eaed]">
                      {campaign.name}
                    </h3>
                    <p className="mt-1 text-sm text-[#b8bec6]">
                      {campaign.beschreibung || "Keine Beschreibung"}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between text-sm">
                  <span className="text-[#b8bec6]">
                    {campaign.stufen || 0} Stufen
                  </span>
                  <span
                    className={`badge ${
                      campaign.status === "active"
                        ? "badge-gewonnen"
                        : "badge-pending"
                    }`}
                  >
                    {campaign.status || "inaktiv"}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-[#e8eaed]">Leads zu Kampagne zuweisen</h2>
              <span className="text-xs text-[#6b7280]">Dual-Track Guardrail aktiv</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <select
                value={selectedCampaignId}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                title="Kampagne auswählen"
                aria-label="Kampagne auswählen"
                className="rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed]"
              >
                <option value="">Kampagne auswählen</option>
                {campaignList.map((campaign) => (
                  <option key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </option>
                ))}
              </select>

              <button
                onClick={() => setSelectedLeadIds(leadsWithEmail.slice(0, 20).map((l) => l.id))}
                className="rounded border border-[#2a3040] px-3 py-2 text-sm text-[#b8bec6]"
                disabled={isLeadsLoading || leadsWithEmail.length === 0}
              >
                Top 20 auswählen
              </button>

              <button
                onClick={handleAssign}
                disabled={!selectedCampaignId || selectedLeadIds.length === 0 || assignMutation.isPending}
                className="rounded-md bg-[#00d4aa] px-3 py-2 text-sm font-semibold text-[#0e1117] disabled:opacity-50"
              >
                {assignMutation.isPending
                  ? "Zuweisung..."
                  : `Zuweisen (${selectedLeadIds.length})`}
              </button>
            </div>

            {assignmentSummary && (
              <div className="rounded border border-[#2a3040] bg-[#0e1117] p-3 text-sm">
                <p className="text-[#00d4aa]">Hinzugefügt: {assignmentSummary.added}</p>
                {assignmentSummary.skippedConflicts > 0 && (
                  <p className="text-[#e74c3c]">
                    Übersprungen wegen Sequence-Konflikt: {assignmentSummary.skippedConflicts}
                  </p>
                )}
              </div>
            )}

            {assignMutation.isError && (
              <p className="text-sm text-[#e74c3c]">Zuweisung fehlgeschlagen</p>
            )}

            <div className="max-h-56 overflow-y-auto space-y-1 border-t border-[#2a3040] pt-3">
              {isLeadsLoading ? (
                <div className="flex items-center gap-2 text-sm text-[#b8bec6]">
                  <Loader2 className="h-4 w-4 animate-spin" /> Lade Leads...
                </div>
              ) : leadsWithEmail.length === 0 ? (
                <p className="text-sm text-[#6b7280]">Keine Leads mit E-Mail verfügbar.</p>
              ) : (
                leadsWithEmail.slice(0, 50).map((lead) => (
                  <label key={lead.id} className="flex items-center gap-2 text-sm text-[#b8bec6]">
                    <input
                      type="checkbox"
                      checked={selectedLeadIds.includes(lead.id)}
                      onChange={() => toggleLead(lead.id)}
                    />
                    <span className="truncate">
                      {lead.firma || `Lead #${lead.id}`} — {lead.email}
                    </span>
                  </label>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
