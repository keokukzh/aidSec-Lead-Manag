"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AlertCircle, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastType = "success" | "error";

export interface ToastMessage {
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (msg: ToastMessage) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const showToast = useCallback((msg: ToastMessage) => {
    setToast(msg);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <div
          className={cn(
            "fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg animate-in slide-in-from-bottom-4",
            toast.type === "success"
              ? "bg-green-900 border border-green-700"
              : "bg-red-900 border border-red-700"
          )}
        >
          {toast.type === "success" ? (
            <CheckCircle className="h-5 w-5 text-green-400" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-400" />
          )}
          <span
            className={cn(
              "text-sm font-medium",
              toast.type === "success" ? "text-green-200" : "text-red-200"
            )}
          >
            {toast.message}
          </span>
          <button
            onClick={() => setToast(null)}
            title="Hinweis schließen"
            aria-label="Hinweis schließen"
            className="ml-2 text-green-400 hover:text-green-200"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
}
