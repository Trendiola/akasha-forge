import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Character {
  id: string;
  project_id: string;
  name: string;
  role: string;
  tagline: string;
  appearance: string;
  appearance_locked: boolean;
  age: string;
  height: string;
  color_palette: string[];
  personality: string;
  traits: string[];
  backstory: string;
  voice: Record<string, any>;
  reference_images: any[];
  outfits: any[];
  expressions: any[];
  props: any[];
  memory: any[];
  relationships: any[];
  version: number;
  created_at: string;
  updated_at: string;
  ai_prompt?: string;
}

export function useCharacters(projectId?: string) {
  return useQuery({
    queryKey: ["characters", projectId],
    enabled: !!projectId,
    queryFn: async (): Promise<Character[]> =>
      (await api.get(`/projects/${projectId}/characters`)).data,
  });
}

export function useCharacter(characterId?: string) {
  return useQuery({
    queryKey: ["character", characterId],
    enabled: !!characterId,
    queryFn: async (): Promise<Character> => (await api.get(`/characters/${characterId}`)).data,
  });
}

export function useCreateCharacter(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Character>): Promise<Character> =>
      (await api.post(`/projects/${projectId}/characters`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["characters", projectId] }),
  });
}

export function useCreateCharacterAI(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { prompt: string; role?: string }): Promise<Character> =>
      (await api.post(`/projects/${projectId}/characters/ai`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["characters", projectId] }),
  });
}

export function useUpdateCharacter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: Partial<Character> & { id: string }): Promise<Character> =>
      (await api.put(`/characters/${id}`, patch)).data,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["character", data.id] });
      qc.invalidateQueries({ queryKey: ["characters", data.project_id] });
    },
  });
}

export function useDeleteCharacter(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => (await api.delete(`/characters/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["characters", projectId] }),
  });
}

export function useCharacterVersions(characterId?: string) {
  return useQuery({
    queryKey: ["character-versions", characterId],
    enabled: !!characterId,
    queryFn: async () => (await api.get(`/characters/${characterId}/versions`)).data,
  });
}

export function useSnapshotCharacter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, label }: { id: string; label?: string }) =>
      (await api.post(`/characters/${id}/versions`, null, { params: { label } })).data,
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: ["character-versions", v.id] }),
  });
}

export function useRestoreVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, versionId }: { id: string; versionId: string }) =>
      (await api.post(`/characters/${id}/versions/${versionId}/restore`)).data,
    onSuccess: (data: Character) => {
      qc.invalidateQueries({ queryKey: ["character", data.id] });
    },
  });
}
