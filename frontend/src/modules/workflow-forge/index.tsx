import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function WorkflowForge() {
  return <ModuleShell module={getModule("workflow-forge")} />;
}
