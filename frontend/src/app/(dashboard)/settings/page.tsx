"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save, Settings as SettingsIcon, Mail, CheckCircle, XCircle, ExternalLink, LogOut, AlertTriangle } from "lucide-react";
import { useState, useEffect } from "react";
import { emailsApi, settingsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

// Toast notification component
function Toast({ message, type, onClose }: { message: string; type: "success" | "error"; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={cn(
      "fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg animate-in slide-in-from-bottom-4",
      type === "success" ? "bg-green-900 border border-green-700" : "bg-red-900 border border-red-700"
    )}>
      {type === "success" ? (
        <CheckCircle className="h-5 w-5 text-green-400" />
      ) : (
        <AlertTriangle className="h-5 w-5 text-red-400" />
      )}
      <span className={cn("text-sm font-medium", type === "success" ? "text-green-200" : "text-red-200")}>
        {message}
      </span>
      <button onClick={onClose} className="ml-2 text-green-400 hover:text-green-200" aria-label="Benachrichtigung schließen">
        <XCircle className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Form state
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPass, setSmtpPass] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");

  const [llmProvider, setLlmProvider] = useState("lm_studio");
  const [llmModel, setLlmModel] = useState("");
  const [openaiUrl, setOpenaiUrl] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");

  const [outlookTenantId, setOutlookTenantId] = useState("");
  const [outlookClientId, setOutlookClientId] = useState("");
  const [outlookClientSecret, setOutlookClientSecret] = useState("");

  // Query for settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const data = await settingsApi.get();
      return data as Record<string, string>;
    },
  });

  // Populate form when settings load
  useEffect(() => {
    if (settings) {
      setSmtpHost(settings.SMTP_HOST || "");
      setSmtpPort(settings.SMTP_PORT || "587");
      setSmtpUser(settings.SMTP_USER || "");
      setSmtpPass(settings.SMTP_PASS || "");
      setSmtpFrom(settings.SMTP_FROM || "");

      setLlmProvider(settings.DEFAULT_PROVIDER || "lm_studio");
      setLlmModel(settings.OPENAI_MODEL || "");
      setOpenaiUrl(settings.OPENAI_BASE_URL || "");
      setOpenaiKey(settings.OPENAI_API_KEY || "");

      setOutlookTenantId(settings.OUTLOOK_TENANT_ID || "");
      setOutlookClientId(settings.OUTLOOK_CLIENT_ID || "");
      setOutlookClientSecret(settings.OUTLOOK_CLIENT_SECRET || "");
    }
  }, [settings]);

  // Query for Outlook status
  const { data: outlookStatus, isLoading: outlookLoading } = useQuery({
    queryKey: ["outlook-status"],
    queryFn: () => emailsApi.getOutlookStatus(),
    refetchInterval: false,
  });

  // Mutation to save SMTP settings
  const saveSmtpMutation = useMutation({
    mutationFn: async () => {
      const data = {
        SMTP_HOST: smtpHost,
        SMTP_PORT: smtpPort,
        SMTP_USER: smtpUser,
        SMTP_PASS: smtpPass,
        SMTP_FROM: smtpFrom,
      };
      await settingsApi.update(data);
    },
    onSuccess: () => {
      setToast({ message: "SMTP-Einstellungen erfolgreich gespeichert!", type: "success" });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (error: Error) => {
      setToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });

  // Mutation to save LLM settings
  const saveLlmMutation = useMutation({
    mutationFn: async () => {
      const data: Record<string, string> = {
        DEFAULT_PROVIDER: llmProvider,
        OPENAI_MODEL: llmModel,
      };
      if (llmProvider === "openai_compatible" || llmProvider === "openai") {
        data.OPENAI_BASE_URL = openaiUrl;
        data.OPENAI_API_KEY = openaiKey;
      }
      await settingsApi.update(data);
    },
    onSuccess: () => {
      setToast({ message: "LLM-Einstellungen erfolgreich gespeichert!", type: "success" });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (error: Error) => {
      setToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });

  // Mutation to save Outlook settings
  const saveOutlookSettingsMutation = useMutation({
    mutationFn: async () => {
      const data = {
        OUTLOOK_TENANT_ID: outlookTenantId,
        OUTLOOK_CLIENT_ID: outlookClientId,
        OUTLOOK_CLIENT_SECRET: outlookClientSecret,
      };
      await settingsApi.update(data);
    },
    onSuccess: () => {
      setToast({ message: "Outlook-Einstellungen erfolgreich gespeichert!", type: "success" });
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (error: Error) => {
      setToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });

  // Mutation to connect Outlook
  const connectMutation = useMutation({
    mutationFn: async () => {
      return emailsApi.connectOutlook();
    },
    onSuccess: (data) => {
      window.location.href = data.authorization_url;
    },
  });

  // Mutation to disconnect Outlook
  const disconnectMutation = useMutation({
    mutationFn: async () => {
      return emailsApi.disconnectOutlook();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outlook-status"] });
      setToast({ message: "Outlook erfolgreich getrennt!", type: "success" });
    },
    onError: (error: Error) => {
      setToast({ message: `Fehler: ${error.message}`, type: "error" });
    },
  });

  // Handle OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const outlookStatusParam = urlParams.get("outlook");
    const messageParam = urlParams.get("message");
    const codeParam = urlParams.get("code");
    const stateParam = urlParams.get("state");

    if (outlookStatusParam === "connected") {
      window.history.replaceState({}, document.title, window.location.pathname);
      queryClient.invalidateQueries({ queryKey: ["outlook-status"] });
      setTimeout(() => setToast({ message: "Outlook erfolgreich verbunden!", type: "success" }), 100);
    } else if (outlookStatusParam === "error") {
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => setToast({ message: messageParam || "Verbindung zu Outlook fehlgeschlagen", type: "error" }), 100);
    } else if (codeParam) {
      // If code is present directly in the URL (e.g. redirected to /settings?code=...)
      const exchangeCode = async () => {
        try {
          // Get token for authentication
          const authData = localStorage.getItem("aidsec-auth");
          let token = "";
          if (authData) {
            try {
              const parsed = JSON.parse(authData);
              token = parsed.state?.token || "";
            } catch (e) {
              console.error("Auth data parse error", e);
            }
          }

          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/emails/outlook/callback?code=${codeParam}&state=${stateParam || ""}`, {
            method: "POST",
            headers: {
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            }
          });
          
          window.history.replaceState({}, document.title, window.location.pathname);
          
          if (response.ok) {
            queryClient.invalidateQueries({ queryKey: ["outlook-status"] });
            setTimeout(() => setToast({ message: "Outlook erfolgreich verbunden!", type: "success" }), 100);
          } else {
            const errorData = await response.json().catch(() => ({ detail: "Fehler beim Verknüpfen des Kontos" }));
            setTimeout(() => setToast({ message: errorData.detail || "Fehler beim Verknüpfen des Kontos", type: "error" }), 100);
          }
        } catch {
          setTimeout(() => setToast({ message: "Verbindungsfehler", type: "error" }), 100);
        }
      };
      exchangeCode();
    }
  }, [queryClient]);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <div>
        <h1 className="text-2xl font-bold text-[#e8eaed]">Einstellungen</h1>
        <p className="text-[#b8bec6]">Konfiguration und Verwaltung</p>
      </div>

      {/* Outlook Connection Status */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center gap-2">
          <Mail className="h-5 w-5 text-[#00d4aa]" />
          <h2 className="text-lg font-semibold text-[#e8eaed]">Outlook-Verbindung</h2>
        </div>

        {outlookLoading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-[#b8bec6]">Prüfe Status...</span>
          </div>
        ) : outlookStatus?.connected ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="h-5 w-5" />
              <span>Verbunden als {outlookStatus.user_email}</span>
            </div>
            <button
              onClick={() => disconnectMutation.mutate()}
              disabled={disconnectMutation.isPending}
              className="flex items-center gap-2 rounded-md bg-[#e74c3c] px-4 py-2 text-white hover:bg-[#c0392b] disabled:opacity-50"
            >
              {disconnectMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <LogOut className="h-4 w-4" />
              )}
              Trennen
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-[#b8bec6]">
              <XCircle className="h-5 w-5" />
              <span>{outlookStatus?.message || "Nicht verbunden"}</span>
            </div>
            <button
              onClick={() => connectMutation.mutate()}
              disabled={connectMutation.isPending}
              className="flex items-center gap-2 rounded-md bg-[#0078d4] px-4 py-2 text-white hover:bg-[#106ebe] disabled:opacity-50"
            >
              {connectMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ExternalLink className="h-4 w-4" />
              )}
              Mit Outlook verbinden
            </button>
          </div>
        )}
      </div>

      {/* SMTP Settings */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5 text-[#00d4aa]" />
            <h2 className="text-lg font-semibold text-[#e8eaed]">SMTP-E-Mail</h2>
          </div>
          <button
            onClick={() => saveSmtpMutation.mutate()}
            disabled={saveSmtpMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {saveSmtpMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Speichern
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm text-[#b8bec6]">SMTP-Host</label>
            <input
              type="text"
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="smtp.example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-[#b8bec6]">SMTP-Port</label>
            <input
              type="number"
              value={smtpPort}
              onChange={(e) => setSmtpPort(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="587"
            />
          </div>
          <div>
            <label className="block text-sm text-[#b8bec6]">Benutzername</label>
            <input
              type="text"
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="user@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-[#b8bec6]">Passwort</label>
            <input
              type="password"
              value={smtpPass}
              onChange={(e) => setSmtpPass(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="••••••••"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm text-[#b8bec6]">Absender-E-Mail</label>
            <input
              type="email"
              value={smtpFrom}
              onChange={(e) => setSmtpFrom(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="noreply@example.com"
            />
          </div>
        </div>
      </div>

      {/* LLM Settings */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5 text-[#00d4aa]" />
            <h2 className="text-lg font-semibold text-[#e8eaed]">LLM-Einstellungen</h2>
          </div>
          <button
            onClick={() => saveLlmMutation.mutate()}
            disabled={saveLlmMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {saveLlmMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Speichern
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm text-[#b8bec6]">Provider</label>
            <select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              aria-label="LLM Provider auswählen"
            >
              <option value="lm_studio">LM Studio</option>
              <option value="openai_compatible">OpenAI Compatible</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-[#b8bec6]">Modell</label>
            <input
              type="text"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="MiniMax-M2.5"
            />
          </div>
          {(llmProvider === "openai_compatible" || llmProvider === "openai") && (
            <>
              <div>
                <label className="block text-sm text-[#b8bec6]">API URL</label>
                <input
                  type="text"
                  value={openaiUrl}
                  onChange={(e) => setOpenaiUrl(e.target.value)}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
                  placeholder="https://api.openai.com/v1"
                />
              </div>
              <div>
                <label className="block text-sm text-[#b8bec6]">API Key</label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
                  placeholder="sk-..."
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Outlook Settings */}
      <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5 text-[#00d4aa]" />
            <h2 className="text-lg font-semibold text-[#e8eaed]">Outlook-Integration (Azure AD)</h2>
          </div>
          <button
            onClick={() => saveOutlookSettingsMutation.mutate()}
            disabled={saveOutlookSettingsMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#00d4aa] px-4 py-2 text-sm font-semibold text-[#0e1117] hover:bg-[#00e8bb] disabled:opacity-50"
          >
            {saveOutlookSettingsMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Speichern
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm text-[#b8bec6]">Tenant ID</label>
            <input
              type="text"
              value={outlookTenantId}
              onChange={(e) => setOutlookTenantId(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </div>
          <div>
            <label className="block text-sm text-[#b8bec6]">Client ID</label>
            <input
              type="text"
              value={outlookClientId}
              onChange={(e) => setOutlookClientId(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm text-[#b8bec6]">Client Secret</label>
            <input
              type="password"
              value={outlookClientSecret}
              onChange={(e) => setOutlookClientSecret(e.target.value)}
              className="mt-1 w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-3 py-2 text-[#e8eaed] focus:border-[#00d4aa] focus:outline-none"
              placeholder="••••••••••••••••"
            />
          </div>
        </div>
        <p className="mt-4 text-xs text-[#6b7280]">
          Die Outlook-Integration erfordert eine Azure AD App-Registrierung mit Mail.Send-Berechtigungen.
        </p>
      </div>
    </div>
  );
}
