import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function PluginForge() {
  return <ModuleShell module={getModule("plugin-forge")} />;
}
