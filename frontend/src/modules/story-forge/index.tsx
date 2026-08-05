import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function StoryForge() {
  return <ModuleShell module={getModule("story-forge")} />;
}
