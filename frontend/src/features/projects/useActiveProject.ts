import { useEffect } from "react";
import { useApp } from "@/store/app-context";
import { useProjects } from "./hooks";
import type { Project } from "@/types";

export function useActiveProject(): Project | null {
  const { activeProjectId, setActiveProjectId } = useApp();
  const { data: projects = [], isSuccess } = useProjects();
  useEffect(() => {
    if (isSuccess && activeProjectId && !projects.some((project) => project.id === activeProjectId)) {
      setActiveProjectId(null);
    }
  }, [activeProjectId, isSuccess, projects, setActiveProjectId]);
  return projects.find((p) => p.id === activeProjectId) ?? null;
}
