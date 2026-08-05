import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useProduction(projectId?: string) {
  return useQuery({
    queryKey: ["production", projectId],
    enabled: !!projectId,
    queryFn: async () => (await api.get(`/projects/${projectId}/production`)).data,
  });
}

export function useCreateNode(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { type: string; parent_id?: string | null; title: string; description?: string }) =>
      (await api.post(`/projects/${projectId}/production`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["production", projectId] }),
  });
}

export function useDeleteNode(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/production/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["production", projectId] }),
  });
}
