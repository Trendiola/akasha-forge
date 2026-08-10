import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AppSettings } from "@/types";

const KEY = ["settings"];

export function useSettings() {
  return useQuery({
    queryKey: KEY,
    queryFn: async (): Promise<AppSettings> => (await api.get("/settings")).data,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<AppSettings>): Promise<AppSettings> =>
      (await api.put("/settings", patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
