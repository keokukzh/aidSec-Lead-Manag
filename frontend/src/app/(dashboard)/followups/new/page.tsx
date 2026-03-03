"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { followupsApi, leadsApi } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { ArrowLeft, Loader2, Calendar } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function NewFollowUpPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const leadId = searchParams.get("lead");

  const [datum, setDatum] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 16);
  });
  const [notiz, setNotiz] = useState("");

  const { data: lead, isLoading: leadLoading } = useQuery({
    queryKey: ["lead", leadId],
    queryFn: () => leadsApi.get(leadId!),
    enabled: !!leadId,
  });

  const createMutation = useMutation({
    mutationFn: (data: { lead_id: number; datum: string; notiz: string }) =>
      followupsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["followups"] });
      queryClient.invalidateQueries({ queryKey: ["lead", leadId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-kpis"] });
      showToast({ message: "Follow-up angelegt", type: "success" });
      router.push(leadId ? `/leads/${leadId}` : "/followups");
    },
    onError: (error: Error) => {
      showToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });


  if (!leadId) {
    return (
      <div className="space-y-6">
        <p className="text-[#e74c3c]">Kein Lead angegeben. Bitte von Lead-Detail aus aufrufen.</p>
        <Link href="/leads" className="text-[#00d4aa] hover:underline">
          Zur Leads-Liste
        </Link>
      </div>
    );
  }

  if (leadLoading || !lead) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  const l = lead as { firma?: string; id?: number };
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!datum.trim()) {
      showToast({ message: "Datum ist erforderlich", type: "error" });
      return;
    }
    createMutation.mutate({
      lead_id: parseInt(leadId, 10),
      datum: new Date(datum).toISOString(),
      notiz: notiz.trim(),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href={`/leads/${leadId}`}
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#2a3040] text-[#b8bec6] hover:bg-[#00d4aa22] hover:text-[#00d4aa]"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-[#e8eaed]">Follow-up anlegen</h1>
          <p className="text-[#b8bec6]">Lead: {l.firma || `#${leadId}`}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="max-w-md space-y-6">
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
          <label className="mb-2 block text-sm font-medium text-[#e8eaed]">
            Fällig am
          </label>
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-[#00d4aa]" />
            <input
              type="datetime-local"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
              required
              title="Datum und Uhrzeit für das Follow-up"
              className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
            />
          </div>
        </div>

        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
          <label className="mb-2 block text-sm font-medium text-[#e8eaed]">
            Notiz (optional)
          </label>
          <textarea
            value={notiz}
            onChange={(e) => setNotiz(e.target.value)}
            rows={4}
            placeholder="z.B. Rückruf wegen Angebot..."
            className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] placeholder:text-[#6b7280] focus:border-[#00d4aa] focus:outline-none"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-md bg-[#00d4aa] px-6 py-2 font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Follow-up anlegen"
            )}
          </button>
          <Link
            href={`/leads/${leadId}`}
            className="rounded-md border border-[#2a3040] px-6 py-2 text-[#e8eaed] hover:bg-[#2a3040]"
          >
            Abbrechen
          </Link>
        </div>
      </form>
    </div>
  );
}
