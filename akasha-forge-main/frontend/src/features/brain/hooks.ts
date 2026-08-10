import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useBrainStatus() {
  return useQuery({
    queryKey: ["brain-status"],
    queryFn: async () => (await api.get("/brain/status")).data,
    refetchInterval: 30_000,
  });
}

export function useOptimizePrompt() {
  return useMutation({
    mutationFn: async (payload: { prompt: string; target: string; project_id?: string | null }) =>
      (await api.post("/brain/optimize", payload)).data as { optimized: string; used_context: boolean },
  });
}

export function useAssist() {
  return useMutation({
    mutationFn: async (payload: { message: string; project_id?: string | null }) =>
      (await api.post("/brain/assist", payload)).data as { reply: string; used_context: boolean },
  });
}
