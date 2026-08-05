import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function CharacterForge() {
  return <ModuleShell module={getModule("character-forge")} />;
}
