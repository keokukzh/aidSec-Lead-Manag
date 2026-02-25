"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi } from "@/lib/api";
import { Loader2, AlertCircle, Lightbulb, Plus, Sparkles, Wand2, X, Trash2 } from "lucide-react";
import { useState } from "react";

interface MarketingTracker {
  id: number;
  idea_number: number;
  title?: string;
  description?: string;
  status: string;
  prioritaet: number;
  notizen: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export default function MarketingPage() {
  const queryClient = useQueryClient();
  const [isGenerating, setIsGenerating] = useState(false);
  const [optimizingId, setOptimizingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [generatedIdea, setGeneratedIdea] = useState<{ title: string; description: string } | null>(null);
  const [isCreatingManual, setIsCreatingManual] = useState(false);
  const [manualTitle, setManualTitle] = useState("");
  const [manualDesc, setManualDesc] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["marketing-tracker"],
    queryFn: () => marketingApi.listTracker(),
  });

  const generateMutation = useMutation({
    mutationFn: () => marketingApi.generate(undefined, "Generiere eine neue Marketing-Taktik"),
    onSuccess: (data) => {
      if (data.success && data.title && data.description) {
        setGeneratedIdea({ title: data.title, description: data.description });
      } else {
        alert("Fehler beim Generieren der Idee: " + (data.error || "Unbekannter Fehler"));
      }
    },
    onSettled: () => setIsGenerating(false),
  });

  const optimizeMutation = useMutation({
    mutationFn: (idea: MarketingTracker) => marketingApi.optimize(idea.id, idea.title || "", idea.description || ""),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-tracker"] });
    },
    onSettled: () => setOptimizingId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => marketingApi.deleteTracker(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-tracker"] });
    },
    onSettled: () => setDeletingId(null),
  });

  const saveMutation = useMutation({
    mutationFn: (idea: { title: string; description: string }) => 
      marketingApi.createTracker({ custom_title: idea.title, custom_description: idea.description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["marketing-tracker"] });
      setGeneratedIdea(null);
      setIsCreatingManual(false);
      setManualTitle("");
      setManualDesc("");
    },
    onError: (err: Error) => {
      alert("Fehler beim Speichern: " + (err.message || "Unbekannter Fehler"));
    }
  });

  const handleGenerate = () => {
    setIsGenerating(true);
    generateMutation.mutate();
  };

  const handleOptimize = (idea: MarketingTracker) => {
    setOptimizingId(idea.id);
    optimizeMutation.mutate(idea);
  };

  const handleSaveIdea = () => {
    if (generatedIdea) {
      saveMutation.mutate(generatedIdea);
    }
  };

  const handleSaveManualIdea = () => {
    if (manualTitle.trim()) {
      saveMutation.mutate({ title: manualTitle, description: manualDesc });
    }
  };

  const handleDelete = (id: number) => {
    if (confirm("Möchten Sie diese Idee wirklich löschen?")) {
      setDeletingId(id);
      deleteMutation.mutate(id);
    }
  };

  const ideas: MarketingTracker[] = (data as MarketingTracker[]) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Marketing Ideen</h1>
          <p className="text-[#b8bec6]">Ideen und Konzepte sammeln</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 rounded-md bg-[#1a1f2e] border border-[#2a3040] px-4 py-2 font-semibold text-[#b8bec6] hover:bg-[#2a3040] transition-colors disabled:opacity-50"
          >
            {isGenerating ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5 text-purple-400" />}
            KI Idee generieren
          </button>
          <button 
            onClick={() => setIsCreatingManual(true)} 
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] transition-colors"
          >
            <Plus className="h-5 w-5" />
            Neue Idee
          </button>
        </div>
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
          {ideas.map((idea: MarketingTracker) => (
            <div
              key={idea.id}
              className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 transition-all hover:border-[#00d4aa]"
            >
              <div className="mb-2 flex items-start justify-between">
                <h3 className="font-semibold text-[#e8eaed]">{idea.title}</h3>
              </div>
              <p className="mb-4 text-sm text-[#b8bec6] whitespace-pre-wrap">
                {idea.description || "Keine Beschreibung"}
              </p>
              <div className="flex items-center justify-between mt-auto">
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
                <button
                  onClick={() => handleOptimize(idea)}
                  disabled={optimizingId === idea.id}
                  title="Strategie verbessern & Actionable Steps generieren"
                  className="p-2 text-[#b8bec6] hover:text-purple-400 transition-colors disabled:opacity-50 rounded bg-[#1a1f2e] border border-[#2a3040] hover:border-purple-400/50"
                >
                  {optimizingId === idea.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                </button>
                <button
                  onClick={() => handleDelete(idea.id)}
                  disabled={deletingId === idea.id}
                  title="Idee löschen"
                  className="p-2 text-[#b8bec6] hover:text-[#e74c3c] transition-colors disabled:opacity-50 rounded bg-[#1a1f2e] border border-[#2a3040] hover:border-[#e74c3c]/50 ml-2"
                >
                  {deletingId === idea.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Generated Idea Modal */}
      {generatedIdea && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#1a1f2e] border border-[#2a3040] rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-[#2a3040] flex justify-between items-center bg-[#0e1117]/50">
              <h2 className="text-xl font-bold text-[#e8eaed] flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-purple-400" />
                KI Marketing-Idee
              </h2>
              <button 
                onClick={() => setGeneratedIdea(null)}
                className="text-[#b8bec6] hover:text-white transition-colors"
                title="Schliessen"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <h3 className="text-lg font-semibold text-[#00d4aa] mb-4">{generatedIdea.title}</h3>
              <div className="text-[#b8bec6] whitespace-pre-wrap leading-relaxed">
                {generatedIdea.description}
              </div>
            </div>
            <div className="p-6 border-t border-[#2a3040] flex justify-end gap-3 bg-[#0e1117]/50">
              <button 
                onClick={() => setGeneratedIdea(null)}
                className="px-4 py-2 rounded-md font-semibold text-[#b8bec6] hover:bg-[#2a3040] transition-colors"
              >
                Verwerfen
              </button>
              <button 
                onClick={handleSaveIdea}
                disabled={saveMutation.isPending}
                className="px-4 py-2 rounded-md font-semibold bg-[#00d4aa] text-[#0e1117] hover:bg-[#00e8bb] transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {saveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Idee speichern
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Manual Idea Modal */}
      {isCreatingManual && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#1a1f2e] border border-[#2a3040] rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col">
            <div className="p-6 border-b border-[#2a3040] flex justify-between items-center bg-[#0e1117]/50">
              <h2 className="text-xl font-bold text-[#e8eaed] flex items-center gap-2">
                <Plus className="h-5 w-5 text-[#00d4aa]" />
                Manuelle Idee hinzufügen
              </h2>
              <button 
                onClick={() => setIsCreatingManual(false)}
                className="text-[#b8bec6] hover:text-white transition-colors"
                title="Schliessen"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#b8bec6] mb-1">
                  Titel der Idee
                </label>
                <input
                  type="text"
                  value={manualTitle}
                  onChange={(e) => setManualTitle(e.target.value)}
                  className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-white focus:border-[#00d4aa] focus:outline-none"
                  placeholder="Z.B. Neuer Blog-Post über Phishing"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#b8bec6] mb-1">
                  Beschreibung
                </label>
                <textarea
                  value={manualDesc}
                  onChange={(e) => setManualDesc(e.target.value)}
                  className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-2 text-white focus:border-[#00d4aa] focus:outline-none min-h-[150px]"
                  placeholder="Detaillierte Schritte..."
                />
              </div>
            </div>
            <div className="p-6 border-t border-[#2a3040] flex justify-end gap-3 bg-[#0e1117]/50">
              <button 
                onClick={() => setIsCreatingManual(false)}
                className="px-4 py-2 rounded-md font-semibold text-[#b8bec6] hover:bg-[#2a3040] transition-colors"
              >
                Abbrechen
              </button>
              <button 
                onClick={handleSaveManualIdea}
                disabled={saveMutation.isPending || !manualTitle.trim()}
                className="px-4 py-2 rounded-md font-semibold bg-[#00d4aa] text-[#0e1117] hover:bg-[#00e8bb] transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {saveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Idee speichern
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
