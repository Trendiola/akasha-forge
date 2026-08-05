import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { ProductionBoard } from "@/features/production/ProductionBoard";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function VideoForge() {
  const mod = getModule("video-forge");
  const project = useActiveProject();
  return (
    <ModuleShell
      module={mod}
      content={{
        timeline: <ProductionBoard projectId={project?.id} />,
        shots: <BibleEditor projectId={project?.id} type="camera" accent={mod.accent} />,
      }}
    />
  );
}
