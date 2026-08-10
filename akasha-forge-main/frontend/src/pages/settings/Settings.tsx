import { NavLink, Routes, Route } from "react-router-dom";
import {
  Settings as SettingsIcon,
  Palette,
  Cpu,
  Languages,
  Send,
  HardDrive,
  RefreshCw,
  Keyboard,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { cn } from "@/lib/utils";
import General from "./General";
import Appearance from "./Appearance";
import AIProviders from "./AIProviders";
import { Language, Publishing, Storage, Updates, Shortcuts } from "./panels";

const NAV = [
  { to: "/settings", end: true, label: "General", icon: SettingsIcon },
  { to: "/settings/appearance", label: "Appearance", icon: Palette },
  { to: "/settings/providers", label: "AI Providers", icon: Cpu },
  { to: "/settings/language", label: "Language", icon: Languages },
  { to: "/settings/publishing", label: "Publishing", icon: Send },
  { to: "/settings/storage", label: "Storage", icon: HardDrive },
  { to: "/settings/updates", label: "Updates", icon: RefreshCw },
  { to: "/settings/shortcuts", label: "Shortcuts", icon: Keyboard },
];

export default function Settings() {
  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader
        icon={SettingsIcon}
        title="Settings"
        tagline="System"
        description="Configure Akasha Forge — providers, appearance, storage and more."
      />
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[240px_1fr]">
        <nav className="space-y-1" data-testid="settings-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              data-testid={`settings-nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                )
              }
            >
              <item.icon className="h-[18px] w-[18px]" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="min-w-0">
          <Routes>
            <Route index element={<General />} />
            <Route path="appearance" element={<Appearance />} />
            <Route path="providers" element={<AIProviders />} />
            <Route path="language" element={<Language />} />
            <Route path="publishing" element={<Publishing />} />
            <Route path="storage" element={<Storage />} />
            <Route path="updates" element={<Updates />} />
            <Route path="shortcuts" element={<Shortcuts />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
