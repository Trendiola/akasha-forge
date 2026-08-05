import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function StoryForge() {
  const mod = getModule("story-forge");
  const project = useActiveProject();
  return (
    <ModuleShell
      module={mod}
      content={{ bible: <BibleEditor projectId={project?.id} type="story" accent={mod.accent} /> }}
    />
  );
}
