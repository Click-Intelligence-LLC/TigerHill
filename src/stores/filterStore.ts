import { create } from "zustand";

interface FilterState {
  model: string;
  status: string;
  provider: string;
  search: string;
  startDate: string;
  endDate: string;
  setFilter: (
    key: "model" | "status" | "provider" | "search" | "startDate" | "endDate",
    value: string,
  ) => void;
  resetFilters: () => void;
  toQueryParams: () => Record<string, string>;
}

export const useFilterStore = create<FilterState>((set, get) => ({
  model: "",
  status: "",
  provider: "",
  search: "",
  startDate: "",
  endDate: "",
  setFilter: (key, value) => set({ [key]: value }),
  resetFilters: () =>
    set({
      model: "",
      status: "",
      provider: "",
      search: "",
      startDate: "",
      endDate: "",
    }),
  toQueryParams: () => {
    const state = get();
    const params: Record<string, string> = {};
    if (state.model) params.model = state.model;
    if (state.status) params.status = state.status;
    if (state.provider) params.provider = state.provider;
    if (state.search) params.search = state.search;
    if (state.startDate) params.start_date = state.startDate;
    if (state.endDate) params.end_date = state.endDate;
    return params;
  },
}));
