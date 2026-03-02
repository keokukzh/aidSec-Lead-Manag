"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { followupsApi, type FollowUpItem } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { Clock, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import Link from "next/link";
import { cn } from "@/lib/utils";

export default function FollowupsPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: overdue, isLoading: overdueLoading } = useQuery({
    queryKey: ["followups", "overdue"],
    queryFn: () => followupsApi.list({ due: "overdue" }),
  });

  const { data: today, isLoading: todayLoading } = useQuery({
    queryKey: ["followups", "today"],
    queryFn: () => followupsApi.list({ due: "today" }),
  });

  const { data: upcoming, isLoading: upcomingLoading } = useQuery({
    queryKey: ["followups", "upcoming"],
    queryFn: () => followupsApi.list({ due: "upcoming" }),
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => followupsApi.complete(String(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["followups"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-kpis"] });
      showToast({ message: "Follow-up erledigt", type: "success" });
    },
    onError: (error: Error) => {
      showToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });

  const isLoading = overdueLoading || todayLoading || upcomingLoading;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  const overdueList = overdue || [];
  const todayList = today || [];
  const upcomingList = (upcoming || []).slice(0, 20);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">Follow-ups</h1>
        <p className="text-[#b8bec6]">Fällige und anstehende Aufgaben</p>
      </div>

      {(overdueList.length > 0 || todayList.length > 0) && (
        <div className="rounded-lg border border-[#e74c3c33] bg-[#e74c3c05] p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-[#e8eaed]">
            <AlertCircle className="h-5 w-5 text-[#e74c3c]" />
            Dringend ({overdueList.length + todayList.length})
          </h2>
          <div className="space-y-3">
            {overdueList.map((fu) => (
              <FollowUpRow
                key={fu.id}
                item={fu}
                variant="overdue"
                onComplete={() => completeMutation.mutate(fu.id)}
                isCompleting={completeMutation.isPending}
              />
            ))}
            {todayList.map((fu) => (
              <FollowUpRow
                key={fu.id}
                item={fu}
                variant="today"
                onComplete={() => completeMutation.mutate(fu.id)}
                isCompleting={completeMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {upcomingList.length > 0 && (
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-[#e8eaed]">
            <Clock className="h-5 w-5 text-[#3498db]" />
            Anstehend ({upcomingList.length})
          </h2>
          <div className="space-y-3">
            {upcomingList.map((fu) => (
              <FollowUpRow
                key={fu.id}
                item={fu}
                variant="upcoming"
                onComplete={() => completeMutation.mutate(fu.id)}
                isCompleting={completeMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {overdueList.length === 0 && todayList.length === 0 && upcomingList.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-[#2a3040] bg-[#1a1f2e] py-16">
          <CheckCircle2 className="mb-4 h-12 w-12 text-[#2ecc71]" />
          <p className="text-[#b8bec6]">Keine offenen Follow-ups</p>
        </div>
      )}
    </div>
  );
}

function FollowUpRow({
  item,
  variant,
  onComplete,
  isCompleting,
}: {
  item: FollowUpItem;
  variant: "overdue" | "today" | "upcoming";
  onComplete: () => void;
  isCompleting: boolean;
}) {
  const date = item.datum ? new Date(item.datum) : null;
  const isOverdue = variant === "overdue";

  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg border p-4",
        isOverdue ? "border-[#e74c3c33] bg-[#e74c3c15]" : "border-[#2a3040] bg-[#0e1117]"
      )}
    >
      <div className="min-w-0 flex-1">
        <Link
          href={`/leads/${item.lead_id}`}
          className="font-medium text-[#e8eaed] hover:text-[#00d4aa] hover:underline"
        >
          {item.lead_firma || `Lead #${item.lead_id}`}
        </Link>
        <p className="mt-1 text-sm text-[#b8bec6]">
          {date ? format(date, "d. MMM yyyy, HH:mm", { locale: de }) : "-"}
        </p>
        {item.notiz && (
          <p className="mt-1 text-xs text-[#6b7280]">{item.notiz}</p>
        )}
      </div>
      <button
        onClick={onComplete}
        disabled={isCompleting}
        className="ml-4 flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] disabled:opacity-50 hover:bg-[#00e8bb]"
      >
        {isCompleting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <CheckCircle2 className="h-4 w-4" />
        )}
        Erledigt
      </button>
    </div>
  );
}
