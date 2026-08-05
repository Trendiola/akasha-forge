import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Save, BookMarked } from "lucide-react";
import { useBible, useSaveBible, type BibleSection } from "@/features/bibles/hooks";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

let counter = 0;
const uid = () => `sec-${Date.now()}-${counter++}`;

export function BibleEditor({
  projectId,
  type,
  accent = "#6D3BFF",
}: {
  projectId?: string | null;
  type: string;
  accent?: string;
}) {
  const { data: bible, isLoading } = useBible(projectId ?? undefined, type);
  const save = useSaveBible(projectId ?? "", type);
  const [sections, setSections] = useState<BibleSection[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (bible) setSections(bible.sections ?? []);
  }, [bible]);

  if (!projectId) {
    return (
      <EmptyState
        icon={BookMarked}
        accent={accent}
        title="Select a project"
        description="Bibles are the permanent memory of a project. Choose or create a project to begin."
      />
    );
  }
  if (isLoading) return <div className="h-40 animate-pulse rounded-2xl border border-border bg-card/40" />;

  const update = (id: string, patch: Partial<BibleSection>) => {
    setSections((s) => s.map((x) => (x.id === id ? { ...x, ...patch } : x)));
    setDirty(true);
  };
  const add = () => {
    setSections((s) => [...s, { id: uid(), heading: "", content: "" }]);
    setDirty(true);
  };
  const remove = (id: string) => {
    setSections((s) => s.filter((x) => x.id !== id));
    setDirty(true);
  };
  const persist = async () => {
    await save.mutateAsync(sections);
    setDirty(false);
    toast.success("Bible saved to project memory");
  };

  return (
    <div className="space-y-4" data-testid={`bible-editor-${type}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {sections.length} section{sections.length === 1 ? "" : "s"} · persisted in MongoDB
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={add} data-testid={`bible-add-${type}`}>
            <Plus className="h-3.5 w-3.5" /> Add section
          </Button>
          <Button
            size="sm"
            className="gap-1.5"
            disabled={!dirty || save.isPending}
            onClick={persist}
            data-testid={`bible-save-${type}`}
            style={{ background: accent }}
          >
            <Save className="h-3.5 w-3.5" /> {save.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>

      {sections.length === 0 ? (
        <EmptyState
          icon={BookMarked}
          accent={accent}
          title="No entries yet"
          description="Add your first section — lore, rules, tone, references. Everything is remembered across the whole project."
          action={
            <Button variant="outline" className="gap-2" onClick={add}>
              <Plus className="h-4 w-4" /> Add section
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {sections.map((s) => (
            <div key={s.id} className="rounded-xl border border-border bg-card/50 p-4" data-testid="bible-section">
              <div className="mb-2 flex items-center gap-2">
                <Input
                  value={s.heading}
                  placeholder="Section heading (e.g. Magic System, Tone, Palette)"
                  onChange={(e) => update(s.id, { heading: e.target.value })}
                  className="border-0 bg-transparent px-0 font-heading text-base font-semibold focus-visible:ring-0"
                />
                <Button
                  size="icon"
                  variant="ghost"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={() => remove(s.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <Textarea
                value={s.content}
                placeholder="Write the canon here…"
                rows={4}
                onChange={(e) => update(s.id, { content: e.target.value })}
                className="resize-y bg-background/40"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
