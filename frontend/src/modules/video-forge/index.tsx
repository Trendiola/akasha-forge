import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function VideoForge() {
  return <ModuleShell module={getModule("video-forge")} />;
}
