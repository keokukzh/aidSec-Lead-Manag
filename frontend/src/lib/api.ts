const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
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
  getKpis: () => request<{
    status: Record<string, number>;
    kategorie: Record<string, number>;
    followups: { overdue: number; today: number; upcoming: number };
  }>("/dashboard/kpis"),
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
    return request<{ items: unknown[]; total: number }>(
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
  }) => request<{ subject: string; body: string }>("/emails/generate", {
    method: "POST",
    body: data,
  }),

  send: (data: { lead_id: string; subject: string; body: string }) =>
    request<{ success: boolean; message: string }>("/emails/send", {
      method: "POST",
      body: data,
    }),

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

  connectOutlook: () =>
    request<{
      authorization_url: string;
      state: string;
      message: string;
    }>("/emails/outlook/connect"),

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
