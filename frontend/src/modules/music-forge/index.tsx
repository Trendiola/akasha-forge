import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function MusicForge() {
  const mod = getModule("music-forge");
  const project = useActiveProject();
  return (
    <ModuleShell
      module={mod}
      content={{ themes: <BibleEditor projectId={project?.id} type="music" accent={mod.accent} /> }}
    />
  );
}
