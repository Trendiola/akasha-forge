import { useState } from "react";
import { ChevronsUpDown, Plus, Check } from "lucide-react";
import { useProjects } from "./hooks";
import { CreateProjectDialog } from "./CreateProjectDialog";
import { useApp } from "@/store/app-context";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export function ProjectSelector() {
  const { data: projects = [] } = useProjects();
  const { activeProjectId, setActiveProjectId } = useApp();
  const [dialogOpen, setDialogOpen] = useState(false);
  const active = projects.find((p) => p.id === activeProjectId);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            data-testid="project-selector"
            className="flex h-9 items-center gap-2.5 rounded-lg border border-border bg-secondary/50 px-3 text-sm transition-colors hover:border-primary/40"
          >
            <span
              className="h-4 w-4 rounded-md"
              style={{ background: active?.color ?? "hsl(var(--muted-foreground))" }}
            />
            <span className="max-w-[160px] truncate font-medium">
              {active?.name ?? "No project"}
            </span>
            <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-72">
          <DropdownMenuLabel>Projects</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {projects.length === 0 && (
            <div className="px-2 py-4 text-center text-xs text-muted-foreground">
              No projects yet.
            </div>
          )}
          {projects.map((p) => (
            <DropdownMenuItem
              key={p.id}
              data-testid={`project-option-${p.id}`}
              onClick={() => setActiveProjectId(p.id)}
              className="gap-2.5"
            >
              <span className="h-3.5 w-3.5 rounded" style={{ background: p.color }} />
              <span className="flex-1 truncate">{p.name}</span>
              {p.id === activeProjectId && <Check className="h-4 w-4 text-primary" />}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setDialogOpen(true)}
            data-testid="new-project-menu-item"
            className={cn("gap-2.5 text-primary focus:text-primary")}
          >
            <Plus className="h-4 w-4" /> New project
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateProjectDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </>
  );
}
