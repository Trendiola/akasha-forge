import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";

export default function VoiceForge() {
  return <ModuleShell module={getModule("voice-forge")} />;
}
