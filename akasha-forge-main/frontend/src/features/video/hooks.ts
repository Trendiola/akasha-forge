import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "@/lib/api";

export interface PlanRequest {
  project_id: string;
  prompt: string;
  target_duration_seconds: number;
  clip_duration_seconds: number;
  aspect_ratio: string;
  style?: string;
  language?: string;
}

export interface ProductionStatus {
  project_id: string;
  status: "empty" | "rendering" | "ready_for_export" | "completed" | "failed";
  total_jobs: number;
  draft: number;
  queued: number;
  submitting: number;
  processing: number;
  completed: number;
  failed: number;
  cancelled: number;
  progress: number;
  ready_for_export: boolean;
  final_asset_id: string;
  final_url: string;
  subtitle_asset_id: string;
  errors: Array<Record<string, any>>;
}

export interface ProductionNode {
  id: string;
  project_id: string;
  type: "act" | "scene" | "shot";
  parent_id: string | null;
  title: string;
  description: string;
  order: number;
  status: string;
  meta?: Record<string, any>;
}

export interface RenderJob {
  id: string;
  project_id: string;
  shot_id: string;
  status: string;
  progress: number;
  result_asset_id: string;
  error_code: string;
  error_message: string;
  prompt: string;
}

const TERMINAL_STATUSES = new Set(["completed", "failed", "empty"]);

export function usePlanVideo(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PlanRequest) =>
      (await api.post("/video-projects/plan", body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-nodes", projectId] });
      qc.invalidateQueries({ queryKey: ["production-status", projectId] });
      qc.invalidateQueries({ queryKey: ["video-jobs", projectId] });
    },
  });
}

export function useGenerateJobs(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { project_id: string; aspect_ratio: string }) =>
      (await api.post("/video-jobs/from-plan", body)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["video-jobs", projectId] });
      qc.invalidateQueries({ queryKey: ["production-status", projectId] });
    },
  });
}

export function useProductionStatus(projectId?: string | null) {
  return useQuery({
    queryKey: ["production-status", projectId],
    enabled: !!projectId,
    queryFn: async (): Promise<ProductionStatus> =>
      (await api.get(`/video-projects/${projectId}/production-status`)).data,
  });
}

export function useProductionNodes(projectId?: string | null) {
  return useQuery({
    queryKey: ["production-nodes", projectId],
    enabled: !!projectId,
    queryFn: async (): Promise<ProductionNode[]> => {
      const res = (await api.get(`/projects/${projectId}/production`)).data;
      const flat: ProductionNode[] = [];
      const walk = (arr: any[]) => {
        for (const n of arr ?? []) {
          flat.push(n);
          if (Array.isArray(n.children)) walk(n.children);
        }
      };
      walk(res?.tree ?? []);
      return flat;
    },
  });
}

export function useVideoJobs(projectId?: string | null) {
  return useQuery({
    queryKey: ["video-jobs", projectId],
    enabled: !!projectId,
    queryFn: async (): Promise<RenderJob[]> =>
      (await api.get("/video-jobs", { params: { project_id: projectId } })).data,
  });
}

export function useRetryJob(projectId?: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (jobId: string) =>
      (await api.post(`/video-jobs/${jobId}/retry`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["video-jobs", projectId] });
      qc.invalidateQueries({ queryKey: ["production-status", projectId] });
    },
  });
}

/**
 * Drives production forward. The backend has no auto-advance daemon, so this
 * repeatedly calls POST /produce (each call advances every job one step and
 * returns the fresh derived status) until the run reaches a terminal state
 * (completed / failed / empty). Polling stops on completion, block, or unmount.
 */
export function useProduceRunner(projectId?: string | null) {
  const qc = useQueryClient();
  const [producing, setProducing] = useState(false);
  const [status, setStatus] = useState<ProductionStatus | null>(null);
  const activeRef = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      activeRef.current = false;
    };
  }, []);

  const syncCaches = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["video-jobs", projectId] });
    qc.invalidateQueries({ queryKey: ["production-status", projectId] });
  }, [qc, projectId]);

  const stop = useCallback(() => {
    activeRef.current = false;
    setProducing(false);
  }, []);

  const start = useCallback(async () => {
    if (!projectId || activeRef.current) return;
    activeRef.current = true;
    setProducing(true);
    let guard = 0;
    try {
      // eslint-disable-next-line no-constant-condition
      while (activeRef.current && mountedRef.current) {
        const view: ProductionStatus = (
          await api.post(`/video-projects/${projectId}/produce`, {
            subtitles: true,
            auto_export: true,
          })
        ).data;
        if (!mountedRef.current) break;
        setStatus(view);
        syncCaches();
        // Terminal / blocked conditions — stop driving.
        if (TERMINAL_STATUSES.has(view.status)) break;
        // Export failed (all shots done but assembly errored) → stop & surface.
        if (view.status === "ready_for_export" && (view.errors?.length ?? 0) > 0) break;
        // Blocked: errors surfaced and nothing is actively rendering (e.g. no
        // enabled video provider) → stop instead of polling forever.
        if ((view.errors?.length ?? 0) > 0 && view.submitting + view.processing === 0) break;
        // Safety cap so a stuck backend can never poll forever.
        if (++guard >= 150) break;
        await new Promise((r) => setTimeout(r, 1200));
      }
    } finally {
      if (mountedRef.current) setProducing(false);
      activeRef.current = false;
    }
  }, [projectId, syncCaches]);

  // Stop driving if the project changes.
  useEffect(() => {
    activeRef.current = false;
    setProducing(false);
    setStatus(null);
  }, [projectId]);

  return { producing, status, start, stop };
}
