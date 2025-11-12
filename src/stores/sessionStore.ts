import { create } from "zustand";
import type { Session, SessionSort } from "@/types";

interface SessionState {
  sessions: Session[];
  total: number;
  page: number;
  limit: number;
  sort: SessionSort;
  selectedSessionId?: string;
  isLoading: boolean;
  error: string | null;
  nextCursor?: string | null;
  setSessions: (payload: {
    sessions: Session[];
    total: number;
    nextCursor?: string | null;
  }) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
  setSort: (sort: SessionSort) => void;
  selectSession: (sessionId?: string) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  total: 0,
  page: 1,
  limit: 20,
  sort: "newest",
  selectedSessionId: undefined,
  isLoading: false,
  error: null,
  nextCursor: null,
  setSessions: ({ sessions, total, nextCursor }) =>
    set({
      sessions: sessions ?? [],
      total: total ?? 0,
      nextCursor: nextCursor ?? null,
    }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setPage: (page) => set({ page }),
  setLimit: (limit) => set({ limit }),
  setSort: (sort) => set({ sort }),
  selectSession: (selectedSessionId) => set({ selectedSessionId }),
}));
