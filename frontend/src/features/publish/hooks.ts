import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function usePlatforms() {
  return useQuery({ queryKey: ["publish-platforms"], queryFn: async () => (await api.get("/publish/platforms")).data });
}

export function useCampaigns() {
  return useQuery({ queryKey: ["campaigns"], queryFn: async () => (await api.get("/publish/campaigns")).data });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (p: Record<string, any>) => (await api.post("/publish/campaigns", p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/publish/campaigns/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function usePosts() {
  return useQuery({ queryKey: ["posts"], queryFn: async () => (await api.get("/publish/posts")).data });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (p: Record<string, any>) => (await api.post("/publish/posts", p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["posts"] }),
  });
}

export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/publish/posts/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["posts"] }),
  });
}
