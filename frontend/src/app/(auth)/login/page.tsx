"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Loader2 } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState("");
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      router.push("/");
    }
  }, [isAuthenticated, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");

    if (!password) {
      setLocalError("Bitte Passwort eingeben");
      return;
    }

    const success = await login(password);
    if (success) {
      router.push("/");
    } else {
      setLocalError("Falsches Passwort");
    }
  };

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0e1117]">
        <Loader2 className="h-8 w-8 animate-spin text-[#00d4aa]" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0e1117] p-4">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="mb-8 text-center">
          <div className="mb-4 flex justify-center">
            <Shield className="h-16 w-16 text-[#00d4aa]" />
          </div>
          <h1 className="font-mono text-3xl font-bold tracking-wider">
            <span className="text-[#00d4aa]">Aid</span>
            <span className="text-[#e8eaed]">Sec</span>
          </h1>
          <p className="mt-2 text-sm text-[#b8bec6]">Lead Management Dashboard</p>
        </div>

        {/* Login Form */}
        <div className="rounded-lg border border-[#2a3040] bg-[#1a1f2e] p-8 shadow-lg">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-[#b8bec6]"
              >
                Passwort
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Team-Passwort eingeben..."
                className="w-full rounded-md border border-[#2a3040] bg-[#0e1117] px-4 py-3 text-[#e8eaed] placeholder-[#6b728099] focus:border-[#00d4aa] focus:outline-none focus:ring-1 focus:ring-[#00d4aa]"
                autoFocus
              />
            </div>

            {(localError || useAuthStore.getState().error) && (
              <p className="text-sm text-[#e74c3c]">
                {localError || useAuthStore.getState().error}
              </p>
            )}

            <button
              type="submit"
              disabled={useAuthStore.getState().isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-[#00d4aa] px-4 py-3 font-semibold text-[#0e1117] transition-all hover:bg-[#00e8bb] hover:shadow-lg hover:shadow-[#00d4aa33] disabled:opacity-50"
            >
              {useAuthStore.getState().isLoading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Anmelden...
                </>
              ) : (
                "Anmelden"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
