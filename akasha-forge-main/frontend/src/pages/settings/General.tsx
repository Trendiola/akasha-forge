import { toast } from "sonner";
import { useSettings, useUpdateSettings } from "@/features/settings/hooks";
import { SettingsHeader, SettingRow } from "./primitives";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MODULES } from "@/config/modules";

export default function General() {
  const { data } = useSettings();
  const update = useUpdateSettings();
  const general = data?.general ?? {};

  const patch = async (next: Record<string, unknown>) => {
    await update.mutateAsync({ general: { ...general, ...next } });
    toast.success("Settings saved");
  };

  return (
    <div>
      <SettingsHeader title="General" description="Core workspace behaviour and defaults." />
      <div className="space-y-3">
        <SettingRow title="Autosave" description="Automatically persist changes as you work.">
          <Switch
            checked={!!general.autosave}
            data-testid="setting-autosave"
            onCheckedChange={(v) => patch({ autosave: v })}
          />
        </SettingRow>
        <SettingRow title="Telemetry" description="Share anonymous usage to improve Akasha Forge.">
          <Switch
            checked={!!general.telemetry}
            data-testid="setting-telemetry"
            onCheckedChange={(v) => patch({ telemetry: v })}
          />
        </SettingRow>
        <SettingRow title="Startup module" description="Which module opens when you launch the app.">
          <Select
            value={general.startupModule ?? "akasha-core"}
            onValueChange={(v) => patch({ startupModule: v })}
          >
            <SelectTrigger className="w-52" data-testid="setting-startup">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODULES.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </SettingRow>
      </div>
    </div>
  );
}
