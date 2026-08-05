import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function ImageForge() {
  return <ModuleShell module={getModule("image-forge")} />;
}
