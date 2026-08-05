import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function MusicForge() {
  return <ModuleShell module={getModule("music-forge")} />;
}
