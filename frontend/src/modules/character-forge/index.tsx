import { useState } from "react";
import { toast } from "sonner";
import { Plus, Users, Trash2, Lock, ChevronRight, ImageOff } from "lucide-react";
import { getModule } from "@/config/modules";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { fileUrl } from "@/lib/api";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useCharacters, useCreateCharacter, useDeleteCharacter } from "@/features/characters/hooks";
import { CharacterDetail } from "@/features/characters/CharacterDetail";

const ROLES = ["protagonist", "antagonist", "supporting", "minor"];

export default function CharacterForge() {
  const mod = getModule("character-forge");
  const project = useActiveProject();
  const { data: characters = [] } = useCharacters(project?.id);
  const create = useCreateCharacter(project?.id ?? "");
  const del = useDeleteCharacter(project?.id ?? "");
  const [selected, setSelected] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("supporting");

  if (selected) {
    return <CharacterDetail characterId={selected} onBack={() => setSelected(null)} />;
  }

  const submit = async () => {
    if (!name.trim()) return toast.error("Name is required");
    const c = await create.mutateAsync({ name: name.trim(), role });
    setName(""); setOpen(false); setSelected(c.id);
    toast.success(`${c.name} added to the cast`);
  };

  return (
    <div className="animate-in fade-in duration-500" data-testid="module-character-forge">
      <PageHeader
        icon={mod.icon}
        title={mod.label}
        tagline="Consistency Engine"
        description="The Character Bible. Every generation references locked appearances, palettes, outfits and voice."
        accent={mod.accent}
        actions={
          <Button className="gap-2 font-heading font-semibold" style={{ background: mod.accent }} onClick={() => setOpen(true)} disabled={!project} data-testid="character-new-btn">
            <Plus className="h-4 w-4" /> New character
          </Button>
        }
      />

      {!project ? (
        <EmptyState icon={Users} accent={mod.accent} title="Select a project" description="Characters live inside a project. Choose or create one to build your cast." />
      ) : characters.length === 0 ? (
        <EmptyState icon={Users} accent={mod.accent} title="No characters yet"
          description="Create your first character. Lock their appearance so every AI generation stays perfectly consistent."
          action={<Button className="gap-2" style={{ background: mod.accent }} onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New character</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {characters.map((c) => {
            const primary = c.reference_images?.find((r: any) => r.is_primary) ?? c.reference_images?.[0];
            return (
              <div key={c.id} onClick={() => setSelected(c.id)} data-testid={`character-card-${c.id}`}
                className="group cursor-pointer overflow-hidden rounded-2xl border border-border bg-card/60 transition-all hover:-translate-y-1 hover:border-primary/40">
                <div className="relative flex h-40 items-center justify-center bg-secondary/40">
                  {primary ? (
                    <img src={fileUrl(primary.file_id)} alt={c.name} className="h-full w-full object-cover" />
                  ) : (
                    <ImageOff className="h-8 w-8 text-muted-foreground" />
                  )}
                  {c.appearance_locked && (
                    <Badge className="absolute right-2 top-2 gap-1 bg-primary/90 text-[10px]"><Lock className="h-3 w-3" /> Locked</Badge>
                  )}
                </div>
                <div className="p-4">
                  <div className="flex items-center justify-between">
                    <p className="truncate font-heading font-semibold">{c.name}</p>
                    <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] capitalize">{c.role}</Badge>
                    <span className="text-xs text-muted-foreground">v{c.version}</span>
                    <div className="ml-auto flex gap-0.5">
                      {(c.color_palette ?? []).slice(0, 4).map((col: string, i: number) => (
                        <span key={i} className="h-3 w-3 rounded-full border border-border" style={{ background: col }} />
                      ))}
                    </div>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); del.mutate(c.id); toast.success(`${c.name} removed`); }}
                    className="mt-3 flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive" data-testid={`character-delete-${c.id}`}>
                    <Trash2 className="h-3 w-3" /> Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="glass-strong sm:max-w-md" data-testid="create-character-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-xl">New character</DialogTitle>
            <DialogDescription>Start the Character Bible. You can lock appearance and add references next.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Kael Ardyn" autoFocus data-testid="character-name-input" />
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger data-testid="character-role-select"><SelectValue /></SelectTrigger>
                <SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={submit} disabled={create.isPending} data-testid="character-submit-btn" style={{ background: mod.accent }}>
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
