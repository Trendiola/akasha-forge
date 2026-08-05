import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function WorldForge() {
  const mod = getModule("world-forge");
  const project = useActiveProject();
  return (
    <ModuleShell
      module={mod}
      content={{ atlas: <BibleEditor projectId={project?.id} type="world" accent={mod.accent} /> }}
    />
  );
}
