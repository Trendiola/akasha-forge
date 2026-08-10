import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useImageOperations() {
  return useQuery({ queryKey: ["image-ops"], queryFn: async () => (await api.get("/image/operations")).data });
}

export function useImageJobs(projectId?: string | null) {
  return useQuery({
    queryKey: ["image-jobs", projectId ?? "all"],
    queryFn: async () => (await api.get("/image/jobs", { params: projectId ? { project_id: projectId } : {} })).data,
  });
}

export function useCreateImageJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (p: { operation: string; source_file_id: string; params?: Record<string, any>; project_id?: string | null }) =>
      (await api.post("/image/jobs", p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["image-jobs"] }),
  });
}
