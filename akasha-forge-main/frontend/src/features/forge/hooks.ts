import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ForgeItem {
  id: string;
  project_id: string;
  module: string;
  kind: string;
  title: string;
  data: Record<string, any>;
  order: number;
  created_at: string;
  updated_at: string;
}

export function useForgeItems(projectId?: string | null, module?: string, kind?: string) {
  return useQuery({
    queryKey: ["forge", projectId, module, kind ?? "all"],
    enabled: !!projectId && !!module,
    queryFn: async (): Promise<ForgeItem[]> =>
      (await api.get(`/projects/${projectId}/forge/${module}`, { params: kind ? { kind } : {} })).data,
  });
}

export function useCreateForgeItem(projectId: string, module: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { kind: string; title: string; data?: Record<string, any> }): Promise<ForgeItem> =>
      (await api.post(`/projects/${projectId}/forge/${module}`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forge", projectId, module] }),
  });
}

export function useUpdateForgeItem(projectId: string, module: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: { id: string; title?: string; data?: Record<string, any> }): Promise<ForgeItem> =>
      (await api.put(`/forge-items/${id}`, patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forge", projectId, module] }),
  });
}

export function useDeleteForgeItem(projectId: string, module: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/forge-items/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forge", projectId, module] }),
  });
}
