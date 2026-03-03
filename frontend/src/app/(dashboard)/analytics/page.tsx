"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi, emailsApi } from "@/lib/api";
import {
  MessageSquare,
  MousePointerClick,
  Send,
  Target,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export default function AnalyticsPage() {
  const [trendDays, setTrendDays] = useState<7 | 30>(30);

  const { data: health, isLoading: loadingHealth } = useQuery({
    queryKey: ["conversionHealth"],
    queryFn: () => analyticsApi.getConversionHealth(30),
  });

  const { data: campaignPerf, isLoading: loadingCampaigns } = useQuery({
    queryKey: ["campaignPerformance"],
    queryFn: () => analyticsApi.getCampaignPerformance(),
  });

  const { data: trendData, isLoading: loadingTrends } = useQuery({
    queryKey: ["conversionTrends", trendDays],
    queryFn: () => analyticsApi.getConversionTrends(trendDays),
  });

  const { data: abStats, isLoading: loadingAbStats } = useQuery({
    queryKey: ["abTestingStats"],
    queryFn: () => emailsApi.getAbTestingStats(),
  });

  if (loadingHealth || loadingCampaigns) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-[#00d4aa]"></div>
      </div>
    );
  }

  const m = health?.metrics;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Conversion Health</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Overview of outreach performance and campaign efficiency (Last 30 Days).
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground">Sent Emails</h3>
            <Send className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold">{m?.total_sent || 0}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {m?.delivery_rate || 0}% delivery rate
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground">Avg. Open Rate</h3>
            <MousePointerClick className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold">{m?.open_rate || 0}%</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {m?.opens || 0} unique opens estimated
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground">Reply Rate</h3>
            <MessageSquare className="h-4 w-4 text-[#00d4aa]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[#00d4aa]">{m?.reply_rate || 0}%</span>
          </div>
          <p className="text-xs text-[#00d4aa]/70 mt-1">
            {m?.replies || 0} replies received via Webhook
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground">Conversion To Won</h3>
            <Target className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-500">{m?.conversion_rate || 0}%</span>
          </div>
          <p className="text-xs text-emerald-500/70 mt-1">
            {m?.conversions || 0} prospects won
          </p>
        </div>
      </div>

      {/* Conversion Trend Chart */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Conversion Trends</h2>
          <select
            value={trendDays}
            onChange={(e) => setTrendDays(Number(e.target.value) as 7 | 30)}
            className="rounded-md border border-border bg-muted/40 px-3 py-1.5 text-sm"
            aria-label="Zeitraum für Trend-Chart"
          >
            <option value={7}>7 Tage</option>
            <option value={30}>30 Tage</option>
          </select>
        </div>
        {loadingTrends ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-[#00d4aa]" />
          </div>
        ) : trendData?.trends?.length ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData.trends} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => {
                    const d = new Date(v);
                    return `${d.getDate()}.${d.getMonth() + 1}`;
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [`${value}%`, name]}
                  labelFormatter={(label) => new Date(label).toLocaleDateString("de-CH")}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="open_rate"
                  name="Open Rate"
                  stroke="hsl(var(--muted-foreground))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="reply_rate"
                  name="Reply Rate"
                  stroke="#00d4aa"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="conversion_rate"
                  name="Conversion Rate"
                  stroke="hsl(142, 71%, 45%)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-64 items-center justify-center text-muted-foreground text-sm">
            Keine Trenddaten verfügbar
          </div>
        )}
      </div>

      {/* Campaign Details Table */}
      <h2 className="text-xl font-semibold mt-8 mb-4">Campaign Breakdown</h2>
      <div className="rounded-md border border-border bg-card">
        <div className="grid grid-cols-12 gap-4 border-b border-border p-4 bg-muted/40 font-medium text-sm text-foreground">
          <div className="col-span-3">Campaign Name</div>
          <div className="col-span-2 text-right">Active Leads</div>
          <div className="col-span-2 text-right">Sent Emails</div>
          <div className="col-span-2 text-right">Replies</div>
          <div className="col-span-2 text-right">Reply Rate</div>
          <div className="col-span-1 text-right">Won</div>
        </div>
        <div className="divide-y divide-border">
          {campaignPerf?.campaigns?.length === 0 && (
             <div className="p-4 text-center text-muted-foreground text-sm">No campaigns to display</div>
          )}
          {campaignPerf?.campaigns?.map((camp) => (
            <div key={camp.id} className="grid grid-cols-12 gap-4 p-4 text-sm items-center hover:bg-muted/20 transition-colors">
              <div className="col-span-3 font-medium text-foreground truncate">{camp.name}</div>
              <div className="col-span-2 text-right text-muted-foreground">{camp.active_leads}</div>
              <div className="col-span-2 text-right text-muted-foreground">{camp.sent_emails}</div>
              <div className="col-span-2 text-right text-[#00d4aa]">{camp.replies}</div>
              <div className="col-span-2 text-right text-[#00d4aa]">{camp.reply_rate_pct}%</div>
              <div className="col-span-1 text-right text-emerald-500 font-medium">{camp.won}</div>
            </div>
          ))}
        </div>
      </div>

      {/* A/B Testing Details Table */}
      <h2 className="text-xl font-semibold mt-8 mb-4">A/B Testing: Betreff-Performance</h2>
      <div className="rounded-md border border-border bg-card">
        <div className="grid grid-cols-12 gap-4 border-b border-border p-4 bg-muted/40 font-medium text-sm text-foreground">
          <div className="col-span-6">Subject Line</div>
          <div className="col-span-2 text-right">Sent</div>
          <div className="col-span-2 text-right">Responded</div>
          <div className="col-span-2 text-right">Success Rate</div>
        </div>
        <div className="divide-y divide-border">
          {loadingAbStats && (
            <div className="p-4 text-center text-muted-foreground text-sm">Loading...</div>
          )}
          {!loadingAbStats && (!abStats || abStats.length === 0) && (
             <div className="p-4 text-center text-muted-foreground text-sm">No A/B testing data available</div>
          )}
          {abStats?.map((stat, i) => (
            <div key={i} className="grid grid-cols-12 gap-4 p-4 text-sm items-center hover:bg-muted/20 transition-colors">
              <div className="col-span-6 font-medium text-foreground truncate">{stat.subject}</div>
              <div className="col-span-2 text-right text-muted-foreground">{stat.sent}</div>
              <div className="col-span-2 text-right text-[#00d4aa]">{stat.responded}</div>
              <div className="col-span-2 text-right text-emerald-500 font-medium">{stat.response_rate}%</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
