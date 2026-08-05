import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { ImageEditor } from "@/features/imageEdit/ImageEditor";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function ImageForge() {
  const mod = getModule("image-forge");
  const project = useActiveProject();
  return (
    <ModuleShell
      module={mod}
      requireProject={false}
      content={{
        canvas: <ImageEditor projectId={project?.id} accent={mod.accent} />,
        styles: <BibleEditor projectId={project?.id} type="style" accent={mod.accent} />,
      }}
    />
  );
}
