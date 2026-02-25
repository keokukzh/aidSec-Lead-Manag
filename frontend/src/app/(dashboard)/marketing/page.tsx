"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2, AlertCircle, Lightbulb, Plus } from "lucide-react";

interface MarketingTracker {
  id: number;
  title: string;
  description: string;
  status: string;
  created_at: string;
}

export default function MarketingPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["marketing-tracker"],
    queryFn: async () => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/marketing/tracker`
      );
      if (!response.ok) throw new Error("Failed to fetch");
      return response.json();
    },
  });

  const ideas: MarketingTracker[] = (data as any[]) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Marketing Ideen</h1>
          <p className="text-[#b8bec6]">Ideen und Konzepte sammeln</p>
        </div>
        <button className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb]">
          <Plus className="h-5 w-5" />
          Neue Idee
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
      ) : ideas.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-[#2a3040] bg-[#1a1f2e]">
          <Lightbulb className="mb-4 h-12 w-12 text-[#b8bec6]" />
          <p className="text-[#b8bec6]">Noch keine Marketing-Ideen</p>
          <p className="mt-1 text-sm text-[#6b728099]">
            Sammeln Sie Ihre ersten Ideen
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {ideas.map((idea: any) => (
            <div
              key={idea.id}
              className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 transition-all hover:border-[#00d4aa]"
            >
              <div className="mb-2 flex items-start justify-between">
                <h3 className="font-semibold text-[#e8eaed]">{idea.title}</h3>
              </div>
              <p className="mb-4 text-sm text-[#b8bec6]">
                {idea.description || "Keine Beschreibung"}
              </p>
              <div className="flex items-center justify-between">
                <span
                  className={`badge ${
                    idea.status === "approved"
                      ? "badge-gewonnen"
                      : idea.status === "rejected"
                      ? "badge-verloren"
                      : "badge-pending"
                  }`}
                >
                  {idea.status || "pending"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
