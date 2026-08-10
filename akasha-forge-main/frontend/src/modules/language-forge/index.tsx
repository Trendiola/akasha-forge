import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function LanguageForge() {
  return <ModuleShell module={getModule("language-forge")} />;
}
