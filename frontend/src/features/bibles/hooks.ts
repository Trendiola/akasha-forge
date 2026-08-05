import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface BibleSection {
  id: string;
  heading: string;
  content: string;
}
export interface Bible {
  id: string;
  project_id: string;
  type: string;
  sections: BibleSection[];
  updated_at: string;
}

export function useBible(projectId?: string, type?: string) {
  return useQuery({
    queryKey: ["bible", projectId, type],
    enabled: !!projectId && !!type,
    queryFn: async (): Promise<Bible> =>
      (await api.get(`/projects/${projectId}/bibles/${type}`)).data,
  });
}

export function useBibleList(projectId?: string) {
  return useQuery({
    queryKey: ["bibles", projectId],
    enabled: !!projectId,
    queryFn: async () => (await api.get(`/projects/${projectId}/bibles`)).data,
  });
}

export function useSaveBible(projectId: string, type: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sections: BibleSection[]): Promise<Bible> =>
      (await api.put(`/projects/${projectId}/bibles/${type}`, { sections })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bible", projectId, type] });
      qc.invalidateQueries({ queryKey: ["bibles", projectId] });
    },
  });
}
