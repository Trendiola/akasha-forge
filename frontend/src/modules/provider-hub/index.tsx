import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Cpu, Plus, Plug, Trash2, Pencil, CheckCircle2, AlertCircle, Loader2, KeyRound, Star, Clock } from "lucide-react";
import {
  useProviders, useProviderCategories, useProviderCatalog,
  useCreateProvider, useUpdateProvider, useDeleteProvider, useTestProvider,
} from "@/features/providers/hooks";
import type { Provider } from "@/types";
import { PageHeader } from "@/components/common/PageHeader";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

const ACCENT = "#6D3BFF";

const STATUS: Record<string, { label: string; cls: string; Icon: any }> = {
  ready: { label: "Connected", cls: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10", Icon: CheckCircle2 },
  configured: { label: "Configured", cls: "text-sky-400 border-sky-400/30 bg-sky-400/10", Icon: KeyRound },
  not_configured: { label: "Not Configured", cls: "text-muted-foreground border-border bg-secondary/40", Icon: AlertCircle },
  error: { label: "Failed", cls: "text-red-400 border-red-400/30 bg-red-400/10", Icon: AlertCircle },
  disabled: { label: "Disabled", cls: "text-muted-foreground border-border bg-secondary/40", Icon: AlertCircle },
};

const BRAND: Record<string, string> = {
  OpenAI: "#10A37F", "Google Gemini": "#4285F4", "Anthropic Claude": "#D97757", Anthropic: "#D97757",
  ElevenLabs: "#5B54F0", Suno: "#E11D48", Runway: "#111827", Veo: "#1A73E8", Kling: "#7C3AED",
  Fal: "#EA580C", Replicate: "#111827", "Stability AI": "#7C3AED", "Stable Diffusion": "#7C3AED", DeepL: "#0F2B46",
};

function Logo({ name }: { name: string }) {
  const color = BRAND[name] ?? ACCENT;
  const initial = name.trim().charAt(0).toUpperCase();
  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl font-heading text-lg font-bold text-white" style={{ background: color }}>
      {initial}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? STATUS.not_configured;
  return (
    <Badge variant="outline" className={cn("gap-1.5 rounded-full", s.cls)} data-testid="provider-status">
      <s.Icon className="h-3 w-3" /> {s.label}
    </Badge>
  );
}

function ProviderFormDialog({
  open, onOpenChange, editing, categories, catalog,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  editing?: Provider | null;
  categories: any[];
  catalog: { name: string; category: string; base_url: string; models: string[] }[];
}) {
  const create = useCreateProvider();
  const update = useUpdateProvider();
  const isEdit = !!editing;

  const [name, setName] = useState("");
  const [category, setCategory] = useState("llm");
  const [apiKey, setApiKey] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [models, setModels] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [orgId, setOrgId] = useState("");
  const [notes, setNotes] = useState("");
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(editing?.name ?? "");
    setCategory(editing?.category ?? "llm");
    setApiKey("");
    setDefaultModel(editing?.default_model ?? "");
    setModels((editing?.models ?? []).join(", "));
    setBaseUrl(editing?.base_url ?? "");
    setOrgId(editing?.organization_id ?? "");
    setNotes(editing?.notes ?? "");
    setEnabled(editing?.enabled ?? false);
  }, [open, editing]);

  const applyPreset = (presetName: string) => {
    const p = catalog.find((c) => c.name === presetName);
    if (!p) return;
    setName(p.name);
    setCategory(p.category);
    setBaseUrl(p.base_url);
    setModels(p.models.join(", "));
    setDefaultModel(p.models[0] ?? "");
  };

  const save = async () => {
    if (!name.trim()) return toast.error("Provider name required");
    const modelList = models.split(",").map((m) => m.trim()).filter(Boolean);
    try {
      if (isEdit) {
        const patch: any = {
          id: editing!.id, name: name.trim(), base_url: baseUrl, models: modelList,
          default_model: defaultModel.trim(), organization_id: orgId.trim(), notes, enabled,
        };
        if (apiKey.trim()) patch.api_key = apiKey.trim();
        await update.mutateAsync(patch);
        toast.success(`${name} updated`);
      } else {
        await create.mutateAsync({
          name: name.trim(), category, base_url: baseUrl, models: modelList,
          default_model: defaultModel.trim(), organization_id: orgId.trim(), notes,
          enabled, api_key: apiKey.trim(),
        });
        toast.success(`${name} added`);
      }
      onOpenChange(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Could not save provider. Please try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="provider-form-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">{isEdit ? `Edit ${editing?.name}` : "Add a provider"}</DialogTitle>
          <DialogDescription>Keys are encrypted at rest. No connection is made — this only stores configuration.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {!isEdit && (
            <div className="space-y-1.5">
              <Label>Quick fill from catalog (optional)</Label>
              <Select onValueChange={applyPreset}>
                <SelectTrigger data-testid="provider-preset-select"><SelectValue placeholder="Choose a known provider…" /></SelectTrigger>
                <SelectContent>{catalog.map((c) => <SelectItem key={c.name} value={c.name}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5"><Label>Provider name</Label><Input value={name} onChange={(e) => setName(e.target.value)} data-testid="provider-name-input" /></div>
            <div className="space-y-1.5">
              <Label>Provider type</Label>
              <Select value={category} onValueChange={setCategory} disabled={isEdit}>
                <SelectTrigger data-testid="provider-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>{categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>API key {editing?.configured && <span className="text-xs text-muted-foreground">(current: {editing.api_key_masked})</span>}</Label>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={editing?.configured ? "Enter to replace…" : "sk-…"} data-testid="provider-key-input" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5"><Label>Default model</Label><Input value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} placeholder="e.g. GPT-5.5" data-testid="provider-defaultmodel-input" /></div>
            <div className="space-y-1.5"><Label>Base URL</Label><Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} data-testid="provider-baseurl-input" /></div>
          </div>
          <div className="space-y-1.5"><Label>Models (comma-separated)</Label><Input value={models} onChange={(e) => setModels(e.target.value)} placeholder="GPT-5.5, GPT-5.4" data-testid="provider-models-input" /></div>
          <div className="space-y-1.5"><Label>Organization ID (optional)</Label><Input value={orgId} onChange={(e) => setOrgId(e.target.value)} data-testid="provider-org-input" /></div>
          <div className="space-y-1.5"><Label>Notes</Label><Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="provider-notes-input" /></div>
          <div className="flex items-center justify-between rounded-xl border border-border bg-card/40 px-4 py-3">
            <div><p className="text-sm font-medium">Enable provider</p><p className="text-xs text-muted-foreground">Disabled providers never appear inside any Forge.</p></div>
            <Switch checked={enabled} onCheckedChange={setEnabled} data-testid="provider-enable-switch" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={save} disabled={create.isPending || update.isPending} data-testid="provider-form-save">{isEdit ? "Save changes" : "Add provider"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ProviderCard({ p, onEdit }: { p: Provider; onEdit: (p: Provider) => void }) {
  const update = useUpdateProvider();
  const del = useDeleteProvider();
  const test = useTestProvider();

  const modelOptions = useMemo(() => {
    const set = new Set<string>(p.models ?? []);
    if (p.default_model) set.add(p.default_model);
    return Array.from(set);
  }, [p.models, p.default_model]);

  const runTest = async () => {
    try {
      const res = await test.mutateAsync(p.id);
      const ms = res.response_ms != null ? ` (${res.response_ms}ms)` : "";
      if (res.status === "ready") toast.success(`Connected${ms} — ${res.message}`);
      else toast.error(`Failed${ms} — ${res.message}`);
    } catch { toast.error("Test failed. Please try again."); }
  };

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-card/50 p-5 transition-colors hover:border-primary/40" data-testid={`provider-card-${p.id}`}>
      <div className="flex items-start gap-3">
        <Logo name={p.name} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate font-heading text-base font-semibold">{p.name}</p>
            {p.is_default && <Star className="h-3.5 w-3.5 text-primary" />}
          </div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{p.category}</p>
        </div>
        <Switch checked={p.enabled} data-testid={`provider-toggle-${p.id}`}
          onCheckedChange={async (v) => { await update.mutateAsync({ id: p.id, enabled: v }); toast.success(`${p.name} ${v ? "enabled" : "disabled"}`); }} />
      </div>

      <div className="mt-4 flex items-center justify-between">
        <StatusBadge status={p.status} />
        <span className="text-xs text-muted-foreground">{p.enabled ? "Enabled" : "Disabled"}</span>
      </div>

      <div className="mt-4 space-y-1.5 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-muted-foreground">API key</span>
          <span className="truncate font-mono" data-testid={`provider-key-${p.id}`}>{p.api_key_masked || "— not set —"}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-muted-foreground">Default model</span>
          {modelOptions.length > 0 ? (
            <Select value={p.default_model || undefined} onValueChange={async (v) => { await update.mutateAsync({ id: p.id, default_model: v }); toast.success("Default model updated"); }}>
              <SelectTrigger className="h-7 flex-1 text-xs" data-testid={`provider-defaultmodel-${p.id}`}><SelectValue placeholder="Select a model" /></SelectTrigger>
              <SelectContent>{modelOptions.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <span className="text-muted-foreground">{p.default_model || "—"}</span>
          )}
        </div>
        {(p.last_test_ms ?? 0) > 0 && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3 w-3" /> Last test {p.last_test_ms}ms
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-border pt-4">
        <Button size="sm" variant="outline" className="flex-1 gap-1.5" onClick={runTest} disabled={test.isPending} data-testid={`provider-test-${p.id}`}>
          {test.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plug className="h-3.5 w-3.5" />} Test
        </Button>
        <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => onEdit(p)} data-testid={`provider-edit-${p.id}`}><Pencil className="h-3.5 w-3.5" /> Edit</Button>
        <button className="text-muted-foreground hover:text-destructive" onClick={() => { del.mutate(p.id); toast.success(`${p.name} removed`); }} data-testid={`provider-delete-${p.id}`}><Trash2 className="h-4 w-4" /></button>
      </div>
    </div>
  );
}

export default function ProviderHub() {
  const { data: providers = [] } = useProviders();
  const { data: categories = [] } = useProviderCategories();
  const { data: catalog = [] } = useProviderCatalog();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Provider | null>(null);

  const openNew = () => { setEditing(null); setFormOpen(true); };
  const openEdit = (p: Provider) => { setEditing(p); setFormOpen(true); };

  return (
    <div className="animate-in fade-in duration-500" data-testid="module-provider-hub">
      <PageHeader
        icon={Cpu}
        title="Provider Hub"
        tagline="AI providers"
        description="The central place to manage every AI provider — keys, models, status and connections."
        accent={ACCENT}
        actions={<Button className="gap-2 font-heading font-semibold" style={{ background: ACCENT }} onClick={openNew} data-testid="provider-add-btn"><Plus className="h-4 w-4" /> Add Provider</Button>}
      />

      {providers.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border px-6 py-16 text-center text-sm text-muted-foreground">
          No providers yet. Add your first provider to get started.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="provider-grid">
          {providers.map((p) => <ProviderCard key={p.id} p={p} onEdit={openEdit} />)}
        </div>
      )}

      <ProviderFormDialog open={formOpen} onOpenChange={setFormOpen} editing={editing} categories={categories} catalog={catalog} />
    </div>
  );
}
