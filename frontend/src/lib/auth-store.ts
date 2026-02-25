"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, ApiError } from "./api";

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  user: string | null;
  isLoading: boolean;
  error: string | null;

  login: (password: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      token: null,
      user: null,
      isLoading: false,
      error: null,

      login: async (password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(password);
          set({
            isAuthenticated: true,
            token: response.access_token,
            user: "admin",
            isLoading: false,
          });
          return true;
        } catch (error) {
          const message = error instanceof ApiError
            ? error.message
            : "Login failed";
          set({
            isLoading: false,
            error: message,
          });
          return false;
        }
      },

      logout: () => {
        set({
          isAuthenticated: false,
          token: null,
          user: null,
          error: null,
        });
      },

      checkAuth: async () => {
        const token = get().token;
        if (!token) {
          set({ isAuthenticated: false });
          return;
        }

        set({ isLoading: true });
        try {
          await authApi.me();
          set({ isAuthenticated: true, isLoading: false });
        } catch {
          set({
            isAuthenticated: false,
            token: null,
            user: null,
            isLoading: false,
          });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "aidsec-auth",
      partialize: (state) => ({
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
