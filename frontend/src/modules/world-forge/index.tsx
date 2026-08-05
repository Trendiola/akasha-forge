import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function WorldForge() {
  return <ModuleShell module={getModule("world-forge")} />;
}
