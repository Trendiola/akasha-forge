import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Provider, ProviderCategory } from "@/types";

const KEY = ["providers"];

export function useProviders(category?: ProviderCategory) {
  return useQuery({
    queryKey: [...KEY, category ?? "all"],
    queryFn: async (): Promise<Provider[]> =>
      (await api.get("/providers", { params: category ? { category } : {} })).data,
  });
}

export function useProviderCategories() {
  return useQuery({
    queryKey: ["provider-categories"],
    queryFn: async () => (await api.get("/provider-categories")).data,
  });
}

export function useProviderCatalog() {
  return useQuery({
    queryKey: ["provider-catalog"],
    queryFn: async () => (await api.get("/provider-catalog")).data as { name: string; category: string; base_url: string; models: string[] }[],
  });
}

export function useUpdateProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: Partial<Provider> & { id: string; api_key?: string }): Promise<Provider> =>
      (await api.put(`/providers/${id}`, patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useCreateProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, any>): Promise<Provider> =>
      (await api.post("/providers", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/providers/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useTestProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.post(`/providers/${id}/test`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
