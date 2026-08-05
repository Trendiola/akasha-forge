import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function PublishForge() {
  return <ModuleShell module={getModule("publish-forge")} />;
}
