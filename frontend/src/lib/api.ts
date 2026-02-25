const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export interface DashboardKpisResponse {
  status: Record<string, number>;
  kategorie: Record<string, number>;
  followups: { overdue: number; today: number; upcoming: number };
  revenue: {
    total_pipeline: number;
    won_deals: number;
    avg_deal_size: number;
  };
}

export interface LeadListItem {
  id: number;
  firma: string | null;
  name: string | null;
  email: string | null;
  telefon: string | null;
  stadt: string | null;
  quelle: string | null;
  status: string;
  kategorie: string | null;
  ranking_score: number | null;
  ranking_grade: string | null;
  lead_score: number | null;
  website: string | null;
  created_at: string | null;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const authData = localStorage.getItem("aidsec-auth");
  if (!authData) return null;
  try {
    const parsed = JSON.parse(authData);
    return parsed.state?.token || null;
  } catch {
    return null;
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const token = await getToken();

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || errorData.message || `HTTP error ${response.status}`
    );
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Auth
export const authApi = {
  login: (password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: { username: "admin", password },
    }),

  logout: () => request<void>("/auth/logout", { method: "POST" }),

  me: () => request<{ user: string }>("/auth/me"),
};

// Dashboard
export const dashboardApi = {
  getKpis: () => request<DashboardKpisResponse>("/dashboard/kpis"),
};

// Leads
export const leadsApi = {
  list: (params?: {
    status?: string;
    kategorie?: string;
    search?: string;
    stadt?: string;
    quelle?: string;
    ranking?: string;
    sort?: string;
    page?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.kategorie) searchParams.set("kategorie", params.kategorie);
    if (params?.search) searchParams.set("search", params.search);
    if (params?.stadt) searchParams.set("stadt", params.stadt);
    if (params?.quelle) searchParams.set("quelle", params.quelle);
    if (params?.ranking) searchParams.set("ranking", params.ranking);
    if (params?.sort) searchParams.set("sort", params.sort);
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const query = searchParams.toString();
    return request<{ items: LeadListItem[]; total: number }>(
      `/leads${query ? `?${query}` : ""}`
    ).then(res => ({
      leads: res.items || [],
      total: res.total || 0
    }));
  },

  get: (id: string) => request<unknown>(`/leads/${id}`),

  create: (data: unknown) =>
    request<unknown>("/leads", { method: "POST", body: data }),

  update: (id: string, data: unknown) =>
    request<unknown>(`/leads/${id}`, { method: "PUT", body: data }),

  delete: (id: string) =>
    request<unknown>(`/leads/${id}`, { method: "DELETE" }),

  bulkStatus: (leadIds: number[], newStatus: string) =>
    request<{ updated: number }>("/leads/bulk-status", {
      method: "POST",
      body: { lead_ids: leadIds, new_status: newStatus }
    }),

  bulkDelete: (leadIds: number[]) =>
    Promise.all(leadIds.map(id => request<unknown>(`/leads/${id}`, { method: "DELETE" }))),

  // Research
  research: (leadId: number) =>
    request<{ lead_id: number; status: string; data: unknown }>(`/leads/${leadId}/research`, { method: "POST" }),

  getResearchStatus: (leadId: number) =>
    request<{ lead_id: number; status: string; last_research: string | null; data: unknown }>(`/leads/${leadId}/research-status`),

  researchMissing: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : "";
    return request<{ processed: number; results: unknown[] }>(`/leads/research-missing${query}`, { method: "POST" });
  },

  bulkResearch: (leadIds: number[]) =>
    request<{ processed: number; results: unknown[] }>("/leads/bulk-research", {
      method: "POST",
      body: leadIds
    }),

  bulkSecurityScan: (leadIds: number[]) =>
    request<{ success: boolean; data: unknown }>("/leads/bulk-security-scan", {
      method: "POST",
      body: { lead_ids: leadIds }
    }),

  // Pipeline
  getPipeline: (perStatus?: number) => {
    const query = perStatus ? `?per_status=${perStatus}` : "";
    return request<Record<string, { items: unknown[]; total: number }>>(`/leads/pipeline${query}`);
  },

  // Timeline
  getTimeline: (leadId: number) =>
    request<Array<{ date: string; type: string; detail: string; status?: string; done?: boolean }>>(`/leads/${leadId}/timeline`),
};

// Campaigns
export const campaignsApi = {
  list: () => request<unknown[]>("/campaigns"),

  get: (id: string) => request<unknown>(`/campaigns/${id}`),

  create: (data: unknown) =>
    request<unknown>("/campaigns", { method: "POST", body: data }),

  update: (id: string, data: unknown) =>
    request<unknown>(`/campaigns/${id}`, { method: "PUT", body: data }),

  delete: (id: string) =>
    request<unknown>(`/campaigns/${id}`, { method: "DELETE" }),
};



// Follow-ups
export const followupsApi = {
  list: (params?: { status?: string; lead_id?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.lead_id) searchParams.set("lead_id", params.lead_id);
    const query = searchParams.toString();
    return request<unknown[]>(`/followups${query ? `?${query}` : ""}`);
  },

  update: (id: string, data: unknown) =>
    request<unknown>(`/followups/${id}`, { method: "PUT", body: data }),

  complete: (id: string) =>
    request<unknown>(`/followups/${id}/complete`, { method: "POST" }),
};

// Ranking - use leads with ranking data
export const rankingApi = {
  leaderboard: (params?: { kategorie?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.kategorie) searchParams.set("kategorie", params.kategorie);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const query = searchParams.toString();
    // Use leads endpoint with sorting by ranking
    return request<{ items: unknown[] }>(`/leads${query ? `?${query}` : ""}&sort=ranking`)
      .then(res => res.items || []);
  },

  analyze: (leadId: string) =>
    request<unknown>(`/ranking/check-lead/${leadId}`, { method: "POST" }),

  batch: (leadIds: number[]) =>
    request<{ job_id: string }>("/ranking/batch", {
      method: "POST",
      body: { lead_ids: leadIds }
    }),

  getBatchStatus: (jobId: string) =>
    request<{
      status: string;
      total: number;
      completed: number;
      errors: number;
      error?: string;
      cancelled?: boolean;
    }>(`/ranking/batch/${jobId}`),
};

// Emails
export const emailsApi = {
  generate: (data: {
    lead_id: string;
    campaign_id?: string;
    stufe?: number;
  }) => request<{ subject?: string; body?: string; betreff?: string; inhalt?: string }>("/emails/generate", {
    method: "POST",
    body: data,
  }).then((res) => ({
    subject: res.subject ?? res.betreff ?? "",
    body: res.body ?? res.inhalt ?? "",
  })),

  send: (data: { lead_id: string; subject: string; body: string }) =>
    request<{ success: boolean; message: string }>("/emails/send", {
      method: "POST",
      body: data,
    }),

  preview: (data: { lead_id: number; template_id: number; preview_type: "desktop" | "mobile" | "plain" }) =>
    request<{
      lead_id: number;
      template_id: number;
      preview_type: string;
      subject: string;
      html: string;
      plain: string;
    }>("/emails/preview", {
      method: "POST",
      body: data,
    }),

  // Templates
  listTemplates: () =>
    request<Array<{
      id: number;
      name: string;
      betreff: string;
      inhalt: string;
      kategorie?: string;
      is_ab_test: boolean;
      version: number;
      variables?: Record<string, unknown>;
      created_at: string;
    }>>("/emails/custom-templates"),

  createTemplate: (data: { name: string; betreff: string; inhalt: string; kategorie?: string }) =>
    request<{
      id: number;
      name: string;
      betreff: string;
      inhalt: string;
    }>("/emails/custom-templates", {
      method: "POST",
      body: data,
    }),

  updateTemplate: (id: number, data: { name?: string; betreff?: string; inhalt?: string; kategorie?: string }) =>
    request<{
      id: number;
      name: string;
      betreff: string;
      inhalt: string;
    }>(`/emails/custom-templates/${id}/extend`, {
      method: "PATCH",
      body: data,
    }),

  deleteTemplate: (id: number) =>
    request<void>(`/emails/custom-templates/${id}`, { method: "DELETE" }),

  duplicateTemplate: (id: number, newName: string) =>
    request<{
      id: number;
      name: string;
      betreff: string;
      inhalt: string;
    }>(`/emails/custom-templates/${id}/duplicate`, {
      method: "POST",
      body: { new_name: newName },
    }),

  getTemplateVersions: (id: number) =>
    request<Array<{ id: number; version: number; name: string; betreff: string; created_at: string }>>(
      `/emails/templates/versions/${id}`
    ),

  // Analytics
  getAnalyticsDashboard: (days: number = 14) =>
    request<{
      overview: {
        total_sent: number;
        delivered: number;
        opened: number;
        clicked: number;
        replied: number;
        bounced: number;
      };
      rates: {
        open_rate: number;
        click_rate: number;
        reply_rate: number;
        bounce_rate: number;
      };
      by_template: Record<string, { sent: number; opened: number; rate: number }>;
      timeline: Array<{ date: string; sent: number; opened: number }>;
    }>(`/emails/analytics?days=${days}`),

  getAnalyticsOverview: () =>
    request<{
      total_sent: number;
      delivered: number;
      opened: number;
      clicked: number;
      replied: number;
      bounced: number;
      open_rate: number;
      click_rate: number;
      response_rate: number;
      bounce_rate: number;
    }>("/emails/analytics/overview"),

  getTemplateAnalytics: () =>
    request<Array<{
      template_id: number;
      template_name: string;
      sent: number;
      opened: number;
      clicked: number;
      replied: number;
      open_rate: number;
      click_rate: number;
      response_rate: number;
    }>>("/emails/analytics/by-template"),

  getAnalyticsByDay: (days: number = 30) =>
    request<Array<{ date: string; sent: number }>>(`/emails/analytics/by-day?days=${days}`),

  // A/B Tests
  listABTests: () =>
    request<Array<{
      id: number;
      name: string;
      template_id?: number;
      subject_a: string;
      subject_b: string;
      distribution_a: number;
      distribution_b: number;
      status: string;
      winner?: string;
      sent_a: number;
      sent_b: number;
      opens_a: number;
      opens_b: number;
      clicks_a: number;
      clicks_b: number;
      created_at: string;
    }>>("/emails/ab-tests"),

  createABTest: (data: {
    name: string;
    template_id?: number;
    subject_a: string;
    subject_b: string;
    distribution_a?: number;
    distribution_b?: number;
    auto_winner_after?: number;
  }) =>
    request<{ id: number }>("/emails/ab-tests", {
      method: "POST",
      body: data,
    }),

  getABTestStats: (id: number) =>
    request<{
      test_id: number;
      name: string;
      status: string;
      winner?: string;
      variant_a: { subject: string; sent: number; opens: number; clicks: number; open_rate: number; click_rate: number };
      variant_b: { subject: string; sent: number; opens: number; clicks: number; open_rate: number; click_rate: number };
    }>(`/emails/ab-tests/${id}/stats`),

  startABTest: (id: number) =>
    request<{ success: boolean }>(`/emails/ab-tests/${id}/start`, { method: "POST" }),

  completeABTest: (id: number, winner: string = "A") =>
    request<{ success: boolean }>(`/emails/ab-tests/${id}/complete?winner=${winner}`, { method: "POST" }),

  // Sequences
  listSequences: () =>
    request<Array<{
      id: number;
      name: string;
      beschreibung?: string;
      steps: Array<{ day_offset: number; template_id?: number; subject_override?: string; body_override?: string }>;
      status: string;
      created_at: string;
      updated_at?: string;
    }>>("/emails/sequences"),

  createSequence: (data: {
    name: string;
    beschreibung?: string;
    steps: Array<{ day_offset: number; template_id?: number; subject_override?: string; body_override?: string }>;
  }) =>
    request<{
      id: number;
      name: string;
      beschreibung?: string;
      steps: Array<{ day_offset: number; template_id?: number; subject_override?: string; body_override?: string }>;
      status: string;
      created_at: string;
      updated_at?: string;
    }>("/emails/sequences", {
      method: "POST",
      body: data,
    }),

  updateSequence: (id: number, data: { name?: string; beschreibung?: string; steps?: unknown[]; status?: string }) =>
    request<{
      id: number;
      name: string;
      beschreibung?: string;
      steps: Array<{ day_offset: number; template_id?: number; subject_override?: string; body_override?: string }>;
      status: string;
      created_at: string;
      updated_at?: string;
    }>(`/emails/sequences/${id}`, {
      method: "PATCH",
      body: data,
    }),

  deleteSequence: (id: number) =>
    request<void>(`/emails/sequences/${id}`, { method: "DELETE" }),

  getSequenceStats: (id: number) =>
    request<{
      sequence_id: number;
      name: string;
      total_assigned: number;
      active: number;
      completed: number;
      paused: number;
      unsubscribed: number;
    }>(`/emails/sequences/${id}/stats`),

  assignLeadsToSequence: (sequenceId: number, leadIds: number[], startNow: boolean = true) =>
    request<{ success: boolean }>(`/emails/sequences/${sequenceId}/assign`, {
      method: "POST",
      body: { lead_ids: leadIds, start_now: startNow },
    }),

  getSequenceLeads: (id: number) =>
    request<Array<{
      assignment_id: number;
      lead_id: number;
      firma: string;
      email: string;
      current_step: number;
      next_send_at?: string;
      status: string;
    }>>(`/emails/sequences/${id}/leads`),

  getSequenceExecutionDueCount: () =>
    request<{
      due_count: number;
      active_assignments: number;
      timestamp: string;
    }>("/emails/sequences/execution/due-count"),

  runSequenceExecution: (limit: number = 50, dryRun: boolean = false) =>
    request<{
      processed: number;
      sent: number;
      failed: number;
      completed: number;
      rescheduled: number;
      paused: number;
      skipped: number;
      dry_run: boolean;
      details: Array<Record<string, unknown>>;
    }>(`/emails/sequences/execution/run?limit=${limit}&dry_run=${dryRun}`, {
      method: "POST",
    }),

  getSequenceWorkerHealth: () =>
    request<{
      enabled: boolean;
      running: boolean;
      last_cycle_at?: string | null;
      last_result?: {
        processed?: number;
        sent?: number;
        failed?: number;
        completed?: number;
      } | null;
      last_error?: string | null;
    }>("/health/sequence-worker"),

  // Bulk Send
  startBulkSend: (data: {
    lead_ids: number[];
    subject: string;
    body: string;
    delay_seconds: number;
    subject_variants?: string[];
  }) =>
    request<{ job_id: string }>("/emails/bulk-send", {
      method: "POST",
      body: data,
    }),

  getBulkStatus: (jobId: string) =>
    request<{
      status: string;
      total: number;
      completed: number;
      sent: number;
      errors: number;
    }>(`/emails/bulk-send/${jobId}`),

  cancelBulkSend: (jobId: string) =>
    request<{ cancelled: boolean }>(`/emails/bulk-send/${jobId}/cancel`, { method: "POST" }),

  // Existing methods
  listDrafts: () =>
    request<Array<{
      id: number;
      lead_id: number;
      lead_firma: string | null;
      betreff: string;
      inhalt: string;
      status: string;
      gesendet_at: string | null;
    }>>("/emails/drafts"),

  updateDraft: (draftId: number, data: { subject: string; body: string }) =>
    request<{ success: boolean }>(`/emails/drafts/${draftId}`, {
      method: "PUT",
      body: data,
    }),

  bulkApproveDrafts: (draftIds: number[]) =>
    request<{ approved: number; failed: number }>("/emails/drafts/bulk-approve", {
      method: "POST",
      body: { draft_ids: draftIds },
    }),

  getAbTestingStats: () =>
    request<Array<{ subject: string; sent: number; responded: number; response_rate: number }>>("/emails/ab-testing"),

  createOutlookDraft: (data: {
    lead_id: string;
    subject: string;
    body: string;
  }) =>
    request<{ success: boolean; web_link?: string; error?: string }>(
      "/emails/outlook-draft",
      {
        method: "POST",
        body: data,
      }
    ),

  // OAuth
  getOutlookStatus: () =>
    request<{
      connected: boolean;
      configured: boolean;
      user_email?: string;
      message: string;
    }>("/emails/outlook/status"),

  connectOutlook: (redirectUri?: string) =>
    request<{
      authorization_url: string;
      state: string;
      message: string;
    }>(`/emails/outlook/connect${redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ""}`),

  disconnectOutlook: () =>
    request<{ success: boolean; message: string }>(
      "/emails/outlook/disconnect",
      { method: "POST" }
    ),

  sendOutlookEmail: (data: {
    lead_id: string;
    subject: string;
    body: string;
  }) =>
    request<{ success: boolean; message: string }>("/emails/outlook/send", {
      method: "POST",
      body: data,
    }),

  getOutlookSentEmails: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : "";
    return request<{
      success: boolean;
      emails: Array<{
        id: string;
        subject: string;
        to: string[];
        sent_at: string;
        preview: string;
      }>;
      total: number;
    }>(`/emails/outlook/sent${query}`);
  },

  checkOutlookConfigured: () =>
    request<{ configured: boolean; user_email?: string }>(
      "/emails/outlook-configured"
    ),

  // Sync
  syncOutlookEmails: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : "";
    return request<{
      success: boolean;
      synced: number;
      matched: number;
      skipped: number;
      errors?: string[];
    }>(`/emails/outlook/sync${query}`, { method: "POST" });
  },

  getSyncedEmails: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : "";
    return request<{
      success: boolean;
      emails: Array<{
        id: number;
        lead_id: number;
        firma: string;
        lead_email: string;
        betreff: string;
        inhalt: string;
        status: string;
        gesendet_at: string | null;
        outlook_message_id: string | null;
        campaign_id: number | null;
      }>;
      total: number;
    }>(`/emails/synced${query}`);
  },
};

// Settings
export const settingsApi = {
  get: () =>
    request<Array<{ key: string; value: string }>>("/settings").then((res) => {
      // Convert array to object
      const obj: Record<string, string> = {};
      for (const item of res) {
        obj[item.key] = item.value;
      }
      return obj;
    }),

  update: (data: Record<string, string>) =>
    request<{ success: boolean; updated: number }>("/settings", {
      method: "PUT",
      body: data,
    }),
};

// Analytics
export const analyticsApi = {
  getConversionHealth: (days: number = 30) =>
    request<{
      period_days: number;
      metrics: {
        total_sent: number;
        total_failed: number;
        delivery_rate: number;
        opens: number;
        open_rate: number;
        replies: number;
        reply_rate: number;
        conversions: number;
        conversion_rate: number;
      };
    }>(`/analytics/conversion-health?days=${days}`),

  getCampaignPerformance: () =>
    request<{
      campaigns: Array<{
        id: number;
        name: string;
        status: string;
        total_leads: number;
        active_leads: number;
        completed: number;
        sent_emails: number;
        failed_emails: number;
        replies: number;
        won: number;
        reply_rate_pct: number;
      }>;
    }>("/analytics/campaign-performance"),
};

// Agent Tasks
export const agentTasksApi = {
  listTasks: (limit: number = 50) =>
    request<Array<{
      id: number;
      task_type: string;
      lead_id: number;
      lead_firma: string | null;
      status: string;
      assigned_to: string | null;
      created_at: string | null;
      completed_at: string | null;
      error_message: string | null;
    }>>(`/tasks?limit=${limit}`),
};

// Import/Export
export const importExportApi = {
  importExcel: async (file: File) => {
    const token = await getToken();
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/import/export`, {
      method: "POST",
      body: formData,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.detail || "Import failed"
      );
    }

    return response.json();
  },

  exportExcel: (params?: { status?: string; kategorie?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.kategorie) searchParams.set("kategorie", params.kategorie);
    const query = searchParams.toString();
    window.open(`${API_BASE_URL}/import/export/download${query ? `?${query}` : ""}`);
  },
};

// Marketing
export const marketingApi = {
  deleteTracker: (trackerId: number) =>
    request<void>(`/marketing/tracker/${trackerId}`, { method: "DELETE" }),

  generate: (category?: string, intent?: string) =>
    request<{ success: boolean; title: string; description: string; error?: string }>("/marketing/generate", {
      method: "POST",
      body: { category, intent }
    }),

  createTracker: (data: { custom_title: string; custom_description: string }) =>
    request<unknown>("/marketing/tracker", {
      method: "POST",
      body: data
    }),

  optimize: (trackerId: number, currentTitle: string, currentDescription: string, category?: string) =>
    request<unknown>(`/marketing/tracker/${trackerId}/optimize`, {
      method: "POST",
      body: {
        current_title: currentTitle,
        current_description: currentDescription,
        category: category
      }
    }),

  listTracker: () => request<Array<{
    id: number;
    idea_number: number;
    status: string;
    prioritaet: number;
    notizen: string | null;
    started_at: string | null;
    completed_at: string | null;
    title?: string;
    description?: string;
  }>>("/marketing/tracker"),

  getIdeas: (params?: { category?: string; budget?: string; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.budget) searchParams.set("budget", params.budget);
    if (params?.search) searchParams.set("search", params.search);
    return request<{ ideas: Record<string, unknown>[]; total: number }>(`/marketing/ideas${searchParams.toString() ? `?${searchParams.toString()}` : ""}`);
  }
};

export { ApiError };
