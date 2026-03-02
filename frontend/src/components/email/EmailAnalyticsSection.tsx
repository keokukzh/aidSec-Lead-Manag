"use client";

import { useQuery } from "@tanstack/react-query";
import { emailsApi } from "@/lib/api";

export function EmailAnalyticsSection() {
  const { data: analytics } = useQuery({
    queryKey: ["email-analytics", 14],
    queryFn: () => emailsApi.getAnalyticsDashboard(14),
    refetchInterval: 60000,
  });

  return (
    <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#e8eaed]">E-Mail Analytics</h2>
        <span className="text-xs text-[#6b7280]">Letzte 14 Tage</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
          <p className="text-xs text-[#b8bec6]">Gesendet</p>
          <p className="text-xl font-semibold text-[#e8eaed]">
            {analytics?.overview?.total_sent ?? 0}
          </p>
        </div>
        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
          <p className="text-xs text-[#b8bec6]">Open Rate</p>
          <p className="text-xl font-semibold text-[#00d4aa]">
            {analytics?.rates?.open_rate ?? 0}%
          </p>
        </div>
        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
          <p className="text-xs text-[#b8bec6]">Click Rate</p>
          <p className="text-xl font-semibold text-[#3498db]">
            {analytics?.rates?.click_rate ?? 0}%
          </p>
        </div>
        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
          <p className="text-xs text-[#b8bec6]">Reply Rate</p>
          <p className="text-xl font-semibold text-[#f39c12]">
            {analytics?.rates?.reply_rate ?? 0}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
          <p className="mb-2 text-sm font-medium text-[#e8eaed]">Templates</p>
          <div className="space-y-2">
            {analytics?.by_template &&
            Object.keys(analytics.by_template).length > 0 ? (
              Object.entries(analytics.by_template).map(([name, value]) => (
                <div
                  key={name}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-[#b8bec6] truncate">{name}</span>
                  <span className="text-[#e8eaed]">
                    {value?.sent ?? 0} gesendet · {value?.rate ?? 0}% open
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#6b7280]">Keine Template-Daten</p>
            )}
          </div>
        </div>
        <div className="rounded-md border border-[#2a3040] bg-[#0e1117] p-3">
          <p className="mb-2 text-sm font-medium text-[#e8eaed]">Timeline</p>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {analytics?.timeline && analytics.timeline.length > 0 ? (
              analytics.timeline.map((item) => (
                <div
                  key={item.date}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-[#b8bec6]">{item.date}</span>
                  <span className="text-[#e8eaed]">
                    {item.sent ?? 0} gesendet · {item.opened ?? 0} geöffnet
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-[#6b7280]">Keine Timeline-Daten</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
