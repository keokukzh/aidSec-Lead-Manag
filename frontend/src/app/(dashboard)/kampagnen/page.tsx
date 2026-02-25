"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignsApi } from "@/lib/api";
import { Loader2, AlertCircle, Plus, Target, X } from "lucide-react";

interface Campaign {
  id: string;
  name: string;
  beschreibung?: string;
  stufen?: number;
  status?: string;
}

export default function KampagnenPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCampaign, setNewCampaign] = useState({ name: "", beschreibung: "" });

  const { data: campaigns, isLoading, error } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => campaignsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; beschreibung: string }) => campaignsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setIsModalOpen(false);
      setNewCampaign({ name: "", beschreibung: "" });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCampaign.name) return;
    createMutation.mutate(newCampaign);
  };

  const campaignList = (campaigns as Campaign[]) || [];

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
      )}
    </div>
  );
}
