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

export function useUpdateProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: Partial<Provider> & { id: string }): Promise<Provider> =>
      (await api.put(`/providers/${id}`, patch)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useCreateProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Provider>): Promise<Provider> =>
      (await api.post("/providers", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
