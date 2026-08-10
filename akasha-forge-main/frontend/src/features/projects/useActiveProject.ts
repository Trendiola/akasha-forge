import { useApp } from "@/store/app-context";
import { useProjects } from "./hooks";
import type { Project } from "@/types";

export function useActiveProject(): Project | null {
  const { activeProjectId } = useApp();
  const { data: projects = [] } = useProjects();
  return projects.find((p) => p.id === activeProjectId) ?? null;
}
