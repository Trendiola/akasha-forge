import { useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, CheckCircle2, FolderKanban, Pencil } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useProjects, useDeleteProject, useUpdateProject } from "@/features/projects/hooks";
import { CreateProjectDialog } from "@/features/projects/CreateProjectDialog";
import { useApp } from "@/store/app-context";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import type { Project } from "@/types";

export default function ProjectsPage() {
  const { data: projects = [], isLoading } = useProjects();
  const del = useDeleteProject();
  const update = useUpdateProject();
  const { activeProjectId, setActiveProjectId } = useApp();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const openEdit = (project: Project) => {
    setEditing(project);
    setEditName(project.name);
    setEditDescription(project.description ?? "");
  };

  const saveEdit = async () => {
    if (!editing || !editName.trim()) return toast.error("Project name is required");
    await update.mutateAsync({ id: editing.id, name: editName.trim(), description: editDescription });
    setEditing(null);
    toast.success("Project updated");
  };

  const remove = async (id: string, name: string) => {
    await del.mutateAsync(id);
    if (activeProjectId === id) setActiveProjectId(null);
    toast.success(`“${name}” deleted`);
  };

  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader
        icon={FolderKanban}
        title="Projects"
        tagline="Workspace"
        description="Manage your creative universes. Each project carries its own bibles, assets and timeline."
        actions={
          <Button className="gap-2 font-heading font-semibold" onClick={() => setDialogOpen(true)} data-testid="projects-new-btn">
            <Plus className="h-4 w-4" /> New project
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-2xl border border-border bg-card/40" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          description="Spin up your first project to begin forging your world."
          action={
            <Button className="gap-2" onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> Create project
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => {
            const isActive = p.id === activeProjectId;
            return (
              <div
                key={p.id}
                data-testid={`project-card-${p.id}`}
                className={cn(
                  "group relative overflow-hidden rounded-2xl border bg-card/60 p-5 transition-all hover:-translate-y-1",
                  isActive ? "border-primary/60 akasha-glow" : "border-border hover:border-primary/30"
                )}
              >
                <div className="absolute inset-x-0 top-0 h-1" style={{ background: p.color }} />
                <div className="flex items-start justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ background: `${p.color}22` }}>
                    <span className="font-display text-lg font-bold" style={{ color: p.color }}>
                      {p.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="rounded-full text-[10px] capitalize">
                      {p.type}
                    </Badge>
                  </div>
                </div>
                <p className="mt-4 truncate font-heading text-base font-semibold">{p.name}</p>
                <p className="mt-1 line-clamp-2 min-h-[2.5rem] text-sm text-muted-foreground">
                  {p.description || "No description yet."}
                </p>

                <div className="mt-4 flex items-center gap-2">
                  <Button
                    size="sm"
                    variant={isActive ? "secondary" : "outline"}
                    className="flex-1 gap-1.5"
                    onClick={() => setActiveProjectId(p.id)}
                    data-testid={`project-activate-${p.id}`}
                  >
                    {isActive ? <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> : null}
                    {isActive ? "Active" : "Set active"}
                  </Button>
                  <Button size="icon" variant="ghost" onClick={() => openEdit(p)} aria-label={`Edit ${p.name}`} data-testid={`project-edit-${p.id}`}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button size="icon" variant="ghost" className="text-muted-foreground hover:text-destructive" data-testid={`project-delete-${p.id}`}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete “{p.name}”?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This permanently removes the project and its workspace context. This cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => remove(p.id, p.name)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          data-testid={`project-confirm-delete-${p.id}`}
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <CreateProjectDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      <Dialog open={Boolean(editing)} onOpenChange={(open) => { if (!open) setEditing(null); }}>
        <DialogContent className="glass-strong sm:max-w-lg">
          <DialogHeader><DialogTitle>Edit project</DialogTitle><DialogDescription>Update the project identity without changing its saved Forge data.</DialogDescription></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5"><Label htmlFor="edit-project-name">Name</Label><Input id="edit-project-name" value={editName} onChange={(e) => setEditName(e.target.value)} /></div>
            <div className="space-y-1.5"><Label htmlFor="edit-project-description">Description</Label><Textarea id="edit-project-description" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={4} /></div>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button><Button onClick={saveEdit} disabled={update.isPending}>{update.isPending ? "Saving…" : "Save changes"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
