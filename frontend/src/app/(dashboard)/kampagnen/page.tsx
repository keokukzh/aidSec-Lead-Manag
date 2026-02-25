"use client";

import { useQuery } from "@tanstack/react-query";
import { campaignsApi } from "@/lib/api";
import { Loader2, AlertCircle, Plus, Target } from "lucide-react";

export default function KampagnenPage() {
  const { data: campaigns, isLoading, error } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => campaignsApi.list(),
  });

  const campaignList = (campaigns as any[]) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Kampagnen</h1>
          <p className="text-[#b8bec6]">E-Mail-Kampagnen verwalten</p>
        </div>
        <button className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb]">
          <Plus className="h-5 w-5" />
          Neue Kampagne
        </button>
      </div>

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
          {campaignList.map((campaign: any) => (
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
