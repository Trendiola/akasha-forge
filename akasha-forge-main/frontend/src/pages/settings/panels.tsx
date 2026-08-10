import { Languages, Send, HardDrive, RefreshCw, Keyboard, CheckCircle2 } from "lucide-react";
import { SettingsHeader, SettingRow } from "./primitives";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const LOCALES = ["English", "Spanish", "French", "German", "Japanese", "Korean", "Portuguese", "Hindi"];
const PLATFORMS = ["YouTube", "Spotify", "Amazon KDP", "Steam", "App Store", "Web"];
const SHORTCUTS = [
  { k: "Ctrl + K", d: "Open command palette" },
  { k: "Ctrl + F", d: "Global search" },
  { k: "Ctrl + N", d: "New project" },
  { k: "Ctrl + \\", d: "Toggle sidebar" },
  { k: "Ctrl + ,", d: "Open settings" },
];

export function Language() {
  return (
    <div>
      <SettingsHeader title="Language" description="Interface language and localization defaults." />
      <div className="space-y-3">
        <SettingRow title="Interface language" description="Language used across the application UI.">
          <Badge variant="outline" className="rounded-full">English (US)</Badge>
        </SettingRow>
        <div className="rounded-xl border border-border bg-card/50 p-4">
          <p className="mb-3 font-medium">Default translation targets</p>
          <div className="flex flex-wrap gap-2">
            {LOCALES.map((l) => (
              <Badge key={l} variant="outline" className="rounded-full border-border bg-secondary/40 px-3 py-1 font-normal">
                {l}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function Publishing() {
  return (
    <div>
      <SettingsHeader title="Publishing" description="Distribution channels and release defaults." />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {PLATFORMS.map((p) => (
          <div key={p} className="flex items-center gap-3 rounded-xl border border-border bg-card/50 px-4 py-3">
            <Send className="h-4 w-4 text-primary" />
            <span className="flex-1 font-medium">{p}</span>
            <Badge variant="outline" className="rounded-full text-[10px]">Not linked</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Storage() {
  return (
    <div>
      <SettingsHeader title="Storage" description="Where assets and project data are stored." />
      <div className="space-y-3">
        <SettingRow title="Storage location" description="Local-first. Desktop builds use the app data directory.">
          <Badge variant="outline" className="gap-1.5 rounded-full">
            <HardDrive className="h-3.5 w-3.5" /> Local
          </Badge>
        </SettingRow>
        <div className="rounded-xl border border-border bg-card/50 p-4">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium">Cache usage</span>
            <span className="text-muted-foreground">0.0 GB / 10 GB</span>
          </div>
          <Progress value={0} className="h-2" />
          <Button variant="outline" size="sm" className="mt-4">Clear cache</Button>
        </div>
      </div>
    </div>
  );
}

export function Updates() {
  return (
    <div>
      <SettingsHeader title="Updates" description="Keep Akasha Forge current." />
      <div className="rounded-xl border border-border bg-card/50 p-6 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15">
          <CheckCircle2 className="h-6 w-6 text-emerald-400" />
        </div>
        <p className="font-heading text-lg font-semibold">You're up to date</p>
        <p className="mt-1 text-sm text-muted-foreground">Version 0.1.0 — Foundation</p>
        <Button variant="outline" className="mt-5 gap-2">
          <RefreshCw className="h-4 w-4" /> Check for updates
        </Button>
      </div>
    </div>
  );
}

export function Shortcuts() {
  return (
    <div>
      <SettingsHeader title="Shortcuts" description="Keyboard shortcuts for a faster workflow." />
      <div className="space-y-2">
        {SHORTCUTS.map((s) => (
          <div key={s.k} className="flex items-center justify-between rounded-xl border border-border bg-card/50 px-4 py-3">
            <span className="flex items-center gap-2 text-sm">
              <Keyboard className="h-4 w-4 text-muted-foreground" />
              {s.d}
            </span>
            <kbd className="rounded-md border border-border bg-background px-2 py-1 font-mono text-xs">{s.k}</kbd>
          </div>
        ))}
      </div>
    </div>
  );
}
