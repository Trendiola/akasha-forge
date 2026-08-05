import { useEffect, useRef, useState } from "react";
import type React from "react";
import { toast } from "sonner";
import {
  ArrowLeft, Save, Lock, Unlock, Plus, Trash2, Star, Upload, History, RotateCcw, Camera, X,
} from "lucide-react";
import { fileUrl, uploadFile } from "@/lib/api";
import {
  useCharacter, useUpdateCharacter, useCharacterVersions, useSnapshotCharacter, useRestoreVersion,
  type Character,
} from "@/features/characters/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
const ACCENT = "#A855F7";

export function CharacterDetail({ characterId, onBack }: { characterId: string; onBack: () => void }) {
  const { data, isLoading } = useCharacter(characterId);
  const update = useUpdateCharacter();
  const snapshot = useSnapshotCharacter();
  const restore = useRestoreVersion();
  const { data: versions = [] } = useCharacterVersions(characterId);
  const [draft, setDraft] = useState<Character | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => { if (data) setDraft(data); }, [data]);

  if (isLoading || !draft) {
    return <div className="h-64 animate-pulse rounded-2xl border border-border bg-card/40" />;
  }

  const set = (patch: Partial<Character>) => setDraft((d) => (d ? { ...d, ...patch } : d));

  const save = async () => {
    await update.mutateAsync({ id: draft.id, ...draft });
    toast.success(`${draft.name} saved`);
  };
  const makeSnapshot = async () => {
    await save();
    await snapshot.mutateAsync({ id: draft.id });
    toast.success("Version snapshot captured");
  };

  const onUpload = async (target: "reference" | "outfit" | "expression", e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    toast.info("Uploading image…");
    try {
      const res = await uploadFile(file, `characters/${draft.id}`);
      if (target === "reference") {
        set({
          reference_images: [
            ...draft.reference_images,
            { id: uid(), file_id: res.id, url: res.url, label: file.name, is_primary: draft.reference_images.length === 0 },
          ],
        });
      }
      toast.success("Image added — click Save to lock it in");
    } catch {
      toast.error("Upload failed");
    }
    e.target.value = "";
  };

  const roleColors: Record<string, string> = {
    protagonist: "#6D3BFF", antagonist: "#F43F5E", supporting: "#A855F7", minor: "#64748B",
  };

  return (
    <div className="animate-in fade-in duration-300" data-testid="character-detail">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack} data-testid="character-back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display text-2xl font-bold">{draft.name || "Unnamed"}</h1>
              <Badge style={{ background: `${roleColors[draft.role] ?? ACCENT}22`, color: roleColors[draft.role] ?? ACCENT }} className="capitalize">
                {draft.role}
              </Badge>
              <Badge variant="outline" className="font-mono text-[10px]">v{draft.version}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">{draft.tagline || "Character Bible"}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={makeSnapshot} data-testid="character-snapshot">
            <History className="h-4 w-4" /> Snapshot
          </Button>
          <Button className="gap-2" onClick={save} disabled={update.isPending} data-testid="character-save" style={{ background: ACCENT }}>
            <Save className="h-4 w-4" /> {update.isPending ? "Saving…" : "Save Bible"}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="appearance">
        <TabsList className="mb-6 h-auto flex-wrap justify-start gap-1 bg-secondary/40 p-1">
          {["appearance", "consistency", "references", "outfits", "expressions", "voice", "personality", "relationships", "props", "memory", "history"].map((t) => (
            <TabsTrigger key={t} value={t} className="rounded-md px-3 py-1.5 text-sm capitalize data-[state=active]:bg-background" data-testid={`char-tab-${t}`}>
              {t}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* APPEARANCE */}
        <TabsContent value="appearance" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Name"><Input value={draft.name} onChange={(e) => set({ name: e.target.value })} data-testid="char-name" /></Field>
            <Field label="Tagline"><Input value={draft.tagline} onChange={(e) => set({ tagline: e.target.value })} /></Field>
            <Field label="Age"><Input value={draft.age} onChange={(e) => set({ age: e.target.value })} placeholder="e.g. 27" /></Field>
            <Field label="Height"><Input value={draft.height} onChange={(e) => set({ height: e.target.value })} placeholder="e.g. 5'11&quot;" /></Field>
          </div>
          <div className="flex items-center justify-between rounded-xl border border-border bg-card/50 px-4 py-3">
            <div className="flex items-center gap-2">
              {draft.appearance_locked ? <Lock className="h-4 w-4 text-primary" /> : <Unlock className="h-4 w-4 text-muted-foreground" />}
              <div>
                <p className="font-medium">Appearance Lock</p>
                <p className="text-xs text-muted-foreground">When locked, every AI generation must match this exact appearance.</p>
              </div>
            </div>
            <Switch checked={draft.appearance_locked} onCheckedChange={(v) => set({ appearance_locked: v })} data-testid="appearance-lock" />
          </div>
          <Field label="Physical Appearance (canon)">
            <Textarea rows={5} value={draft.appearance} onChange={(e) => set({ appearance: e.target.value })} placeholder="Face, build, hair, distinguishing features, signature look…" data-testid="char-appearance" />
          </Field>
          <PaletteEditor palette={draft.color_palette} onChange={(color_palette) => set({ color_palette })} />
        </TabsContent>

        {/* CONSISTENCY */}
        <TabsContent value="consistency" className="space-y-4">
          <div className="rounded-xl border border-border bg-card/50 p-4">
            <div className="flex items-center gap-2">
              {draft.appearance_locked ? <Lock className="h-4 w-4 text-primary" /> : <Unlock className="h-4 w-4 text-muted-foreground" />}
              <p className="font-medium">Appearance {draft.appearance_locked ? "Locked" : "Unlocked"}</p>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {draft.appearance_locked
                ? "Every AI generation must match this character's canon appearance and palette."
                : "Lock appearance (in the Appearance tab) to enforce consistency across generations."}
            </p>
            {draft.color_palette.length > 0 && (
              <div className="mt-3 flex gap-1.5">
                {draft.color_palette.map((c, i) => <span key={i} className="h-6 w-6 rounded-md border border-border" style={{ background: c }} />)}
              </div>
            )}
          </div>
          {draft.ai_prompt ? (
            <div className="rounded-xl border border-border bg-card/50 p-4" data-testid="ai-prompt-block">
              <p className="mb-1 font-heading text-sm font-bold text-primary">Original AI prompt</p>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{draft.ai_prompt}</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No AI prompt stored. Characters created via “Create with AI” keep their prompt here.</p>
          )}
        </TabsContent>

        {/* REFERENCES */}
        <TabsContent value="references" className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{draft.reference_images.length} reference image(s)</p>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={() => fileInput.current?.click()} data-testid="upload-reference">
              <Upload className="h-3.5 w-3.5" /> Upload reference
            </Button>
            <input ref={fileInput} type="file" accept="image/*" className="hidden" onChange={(e) => onUpload("reference", e)} />
          </div>
          {draft.reference_images.length === 0 ? (
            <EmptyBox icon={Camera} text="No reference images. Upload the visual anchors that lock this character's identity." />
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {draft.reference_images.map((img: any) => (
                <div key={img.id} className={cn("group relative overflow-hidden rounded-xl border bg-card/50", img.is_primary ? "border-primary" : "border-border")} data-testid="reference-image">
                  <img src={fileUrl(img.file_id)} alt={img.label} className="aspect-square w-full object-cover" />
                  <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-black/60 px-2 py-1.5 opacity-0 transition-opacity group-hover:opacity-100">
                    <button onClick={() => set({ reference_images: draft.reference_images.map((r: any) => ({ ...r, is_primary: r.id === img.id })) })} title="Set primary">
                      <Star className={cn("h-4 w-4", img.is_primary ? "fill-primary text-primary" : "text-white")} />
                    </button>
                    <button onClick={() => set({ reference_images: draft.reference_images.filter((r: any) => r.id !== img.id) })}>
                      <X className="h-4 w-4 text-white" />
                    </button>
                  </div>
                  {img.is_primary && <Badge className="absolute left-2 top-2 bg-primary text-[10px]">Primary</Badge>}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* OUTFITS / EXPRESSIONS / PROPS / RELATIONSHIPS / MEMORY are list editors */}
        <TabsContent value="outfits">
          <ListEditor items={draft.outfits} fields={["name", "description"]} label="outfit"
            onChange={(outfits) => set({ outfits })} />
        </TabsContent>
        <TabsContent value="expressions">
          <ListEditor items={draft.expressions} fields={["name", "description"]} label="expression"
            onChange={(expressions) => set({ expressions })} />
        </TabsContent>
        <TabsContent value="props">
          <ListEditor items={draft.props} fields={["name", "description"]} label="prop"
            onChange={(props) => set({ props })} />
        </TabsContent>
        <TabsContent value="relationships">
          <ListEditor items={draft.relationships} fields={["name", "type", "description"]} label="relationship"
            onChange={(relationships) => set({ relationships })} />
        </TabsContent>
        <TabsContent value="memory">
          <ListEditor items={draft.memory} fields={["text", "tag"]} label="memory"
            onChange={(memory) => set({ memory })} />
        </TabsContent>

        {/* VOICE */}
        <TabsContent value="voice" className="space-y-4">
          <Field label="Voice description">
            <Textarea rows={3} value={draft.voice?.description ?? ""} onChange={(e) => set({ voice: { ...draft.voice, description: e.target.value } })} placeholder="Timbre, accent, cadence, emotional range…" />
          </Field>
          <Field label="Assigned voice ID (provider)">
            <Input value={draft.voice?.voice_id ?? ""} onChange={(e) => set({ voice: { ...draft.voice, voice_id: e.target.value } })} placeholder="Assigned from Voice provider" />
          </Field>
        </TabsContent>

        {/* PERSONALITY */}
        <TabsContent value="personality" className="space-y-4">
          <Field label="Personality summary">
            <Textarea rows={4} value={draft.personality} onChange={(e) => set({ personality: e.target.value })} placeholder="Core temperament, values, flaws, motivations…" />
          </Field>
          <TagEditor tags={draft.traits} onChange={(traits) => set({ traits })} label="Traits" />
          <Field label="Backstory">
            <Textarea rows={5} value={draft.backstory} onChange={(e) => set({ backstory: e.target.value })} />
          </Field>
        </TabsContent>

        {/* HISTORY */}
        <TabsContent value="history" className="space-y-2">
          {versions.length === 0 ? (
            <EmptyBox icon={History} text="No snapshots yet. Capture a version to preserve this character's state." />
          ) : (
            versions.map((v: any) => (
              <div key={v.id} className="flex items-center justify-between rounded-xl border border-border bg-card/50 px-4 py-3" data-testid="version-row">
                <div>
                  <p className="font-medium">{v.label}</p>
                  <p className="text-xs text-muted-foreground">{new Date(v.created_at).toLocaleString()}</p>
                </div>
                <Button variant="outline" size="sm" className="gap-1.5" onClick={async () => { await restore.mutateAsync({ id: draft.id, versionId: v.id }); toast.success("Version restored"); }}>
                  <RotateCcw className="h-3.5 w-3.5" /> Restore
                </Button>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}

function EmptyBox({ icon: Icon, text }: { icon: React.ElementType; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/40 px-6 py-14 text-center">
      <Icon className="mb-3 h-8 w-8 text-muted-foreground" />
      <p className="max-w-sm text-sm text-muted-foreground">{text}</p>
    </div>
  );
}

function PaletteEditor({ palette, onChange }: { palette: string[]; onChange: (p: string[]) => void }) {
  const [val, setVal] = useState("#6D3BFF");
  return (
    <div className="rounded-xl border border-border bg-card/50 p-4">
      <Label className="mb-3 block">Color Palette</Label>
      <div className="flex flex-wrap items-center gap-2">
        {palette.map((c, i) => (
          <div key={i} className="group relative">
            <span className="block h-8 w-8 rounded-lg border border-border" style={{ background: c }} />
            <button onClick={() => onChange(palette.filter((_, j) => j !== i))} className="absolute -right-1 -top-1 hidden rounded-full bg-black/70 p-0.5 group-hover:block">
              <X className="h-3 w-3 text-white" />
            </button>
          </div>
        ))}
        <input type="color" value={val} onChange={(e) => setVal(e.target.value)} className="h-8 w-10 cursor-pointer rounded border-0 bg-transparent" />
        <Button variant="outline" size="sm" onClick={() => onChange([...palette, val])} data-testid="add-color">Add</Button>
      </div>
    </div>
  );
}

function TagEditor({ tags, onChange, label }: { tags: string[]; onChange: (t: string[]) => void; label: string }) {
  const [val, setVal] = useState("");
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-2 rounded-xl border border-border bg-card/50 p-3">
        {tags.map((t, i) => (
          <Badge key={i} variant="outline" className="gap-1">
            {t}
            <button onClick={() => onChange(tags.filter((_, j) => j !== i))}><X className="h-3 w-3" /></button>
          </Badge>
        ))}
        <input
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && val.trim()) { onChange([...tags, val.trim()]); setVal(""); } }}
          placeholder="Type + Enter"
          className="flex-1 bg-transparent text-sm outline-none"
        />
      </div>
    </div>
  );
}

function ListEditor({ items, fields, label, onChange }: { items: any[]; fields: string[]; label: string; onChange: (i: any[]) => void }) {
  const add = () => onChange([...items, { id: uid(), ...Object.fromEntries(fields.map((f) => [f, ""])) }]);
  const upd = (id: string, f: string, v: string) => onChange(items.map((x) => (x.id === id ? { ...x, [f]: v } : x)));
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={add} data-testid={`add-${label}`}>
          <Plus className="h-3.5 w-3.5" /> Add {label}
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyBox icon={Plus} text={`No ${label}s yet. Add one to enrich the Character Bible.`} />
      ) : (
        items.map((it) => (
          <div key={it.id} className="rounded-xl border border-border bg-card/50 p-4" data-testid={`${label}-row`}>
            <div className="flex items-start gap-3">
              <div className="grid flex-1 gap-2">
                {fields.map((f) =>
                  f === "description" || f === "text" ? (
                    <Textarea key={f} rows={2} value={it[f] ?? ""} placeholder={f} onChange={(e) => upd(it.id, f, e.target.value)} />
                  ) : (
                    <Input key={f} value={it[f] ?? ""} placeholder={f} onChange={(e) => upd(it.id, f, e.target.value)} />
                  )
                )}
              </div>
              <Button size="icon" variant="ghost" className="text-muted-foreground hover:text-destructive" onClick={() => onChange(items.filter((x) => x.id !== it.id))}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
