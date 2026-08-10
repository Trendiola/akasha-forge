import { toast } from "sonner";
import { useSettings, useUpdateSettings } from "@/features/settings/hooks";
import { SettingsHeader, SettingRow } from "./primitives";
import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ACCENTS = ["#6D3BFF", "#A855F7", "#EC4899", "#0EA5E9", "#14B8A6", "#F97316"];

export default function Appearance() {
  const { data } = useSettings();
  const update = useUpdateSettings();
  const appearance = data?.appearance ?? {};

  const patch = async (next: Record<string, unknown>) => {
    await update.mutateAsync({ appearance: { ...appearance, ...next } });
    toast.success("Appearance updated");
  };

  const accent = appearance.accent ?? "#6D3BFF";

  return (
    <div>
      <SettingsHeader title="Appearance" description="Tune the look and feel of your workspace." />
      <div className="space-y-3">
        <SettingRow title="Theme" description="Akasha Forge is optimized for a dark premium canvas.">
          <Select value={appearance.theme ?? "dark"} onValueChange={(v) => patch({ theme: v })}>
            <SelectTrigger className="w-40" data-testid="setting-theme">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dark">Dark</SelectItem>
              <SelectItem value="midnight">Midnight</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>
        </SettingRow>

        <SettingRow title="Accent color" description="The Akasha signature hue across the interface.">
          <div className="flex items-center gap-2">
            {ACCENTS.map((c) => (
              <button
                key={c}
                data-testid={`accent-${c}`}
                onClick={() => {
                  patch({ accent: c });
                  document.documentElement.style.setProperty("--akasha", hexToHsl(c));
                }}
                style={{ background: c }}
                className={cn(
                  "h-6 w-6 rounded-full ring-offset-2 ring-offset-background transition-transform hover:scale-110",
                  accent === c && "ring-2 ring-white"
                )}
              />
            ))}
          </div>
        </SettingRow>

        <SettingRow title="Density" description="Spacing between interface elements.">
          <Select value={appearance.density ?? "comfortable"} onValueChange={(v) => patch({ density: v })}>
            <SelectTrigger className="w-44" data-testid="setting-density">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="compact">Compact</SelectItem>
              <SelectItem value="comfortable">Comfortable</SelectItem>
              <SelectItem value="spacious">Spacious</SelectItem>
            </SelectContent>
          </Select>
        </SettingRow>
      </div>
    </div>
  );
}

function hexToHsl(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  const l = (max + min) / 2;
  const d = max - min;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  if (d !== 0) {
    if (max === r) h = 60 * (((g - b) / d) % 6);
    else if (max === g) h = 60 * ((b - r) / d + 2);
    else h = 60 * ((r - g) / d + 4);
  }
  if (h < 0) h += 360;
  return `${Math.round(h)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}
