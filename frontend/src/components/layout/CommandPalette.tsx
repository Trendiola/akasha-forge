import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { MODULES } from "@/config/modules";
import { useApp } from "@/store/app-context";
import { useProjects } from "@/features/projects/hooks";
import { Settings, FolderOpen, Boxes } from "lucide-react";

const EXTRA = [
  { label: "Assets Library", path: "/assets", icon: Boxes },
  { label: "Projects", path: "/projects", icon: FolderOpen },
  { label: "Settings", path: "/settings", icon: Settings },
];

export function CommandPalette() {
  const { commandOpen, setCommandOpen, setActiveProjectId } = useApp();
  const navigate = useNavigate();
  const { data: projects = [] } = useProjects();

  const go = (path: string) => {
    navigate(path);
    setCommandOpen(false);
  };

  return (
    <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
      <CommandInput placeholder="Search modules, projects and actions…" data-testid="command-input" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Modules">
          {MODULES.map((mod) => {
            const Icon = mod.icon;
            return (
              <CommandItem key={mod.id} value={`${mod.label} ${mod.tagline}`} onSelect={() => go(mod.path)}>
                <Icon className="mr-2 h-4 w-4" />
                <span>{mod.label}</span>
                <span className="ml-auto text-xs text-muted-foreground">{mod.tagline}</span>
              </CommandItem>
            );
          })}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Library">
          {EXTRA.map((e) => {
            const Icon = e.icon;
            return (
              <CommandItem key={e.path} value={e.label} onSelect={() => go(e.path)}>
                <Icon className="mr-2 h-4 w-4" />
                {e.label}
              </CommandItem>
            );
          })}
        </CommandGroup>
        {projects.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Projects">
              {projects.map((p) => (
                <CommandItem
                  key={p.id}
                  value={`project ${p.name}`}
                  onSelect={() => {
                    setActiveProjectId(p.id);
                    go("/");
                  }}
                >
                  <span className="mr-2 h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
                  {p.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
