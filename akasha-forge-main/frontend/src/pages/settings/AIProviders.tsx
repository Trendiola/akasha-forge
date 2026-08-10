import { useState } from "react";
import { toast } from "sonner";
import { Cpu, Star, Plus, Plug, Trash2, CheckCircle2, AlertCircle, Loader2, KeyRound } from "lucide-react";
import {
  useProviders, useProviderCategories, useUpdateProvider, useCreateProvider, useDeleteProvider, useTestProvider,
} from "@/features/providers/hooks";
import type { Provider } from "@/types";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const STATUS: Record<string, { label: string; cls: string; Icon: any }> = {
  ready: { label: "Ready", cls: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10", Icon: CheckCircle2 },
  configured: { label: "Configured", cls: "text-sky-400 border-sky-400/30 bg-sky-400/10", Icon: KeyRound },
  not_configured: { label: "Not Configured", cls: "text-muted-foreground border-border bg-secondary/40", Icon: AlertCircle },
  error: { label: "Error", cls: "text-red-400 border-red-400/30 bg-red-400/10", Icon: AlertCircle },
  disabled: { label: "Disabled", cls: "text-muted-foreground border-border bg-secondary/40", Icon: AlertCircle },
  validating: { label: "Validating", cls: "text-amber-400 border-amber-400/30 bg-amber-400/10", Icon: Loader2 },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? STATUS.not_configured;
  return (
    <Badge variant="outline" className={cn("gap-1.5 rounded-full", s.cls)} data-testid={`provider-status`}>
      <s.Icon className="h-3 w-3" /> {s.label}
    </Badge>
  );
}

function ConfigureDialog({ provider, open, onOpenChange }: { provider: Provider; open: boolean; onOpenChange: (v: boolean) => void }) {
  const update = useUpdateProvider();
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(provider.base_url);
  const [priority, setPriority] = useState(provider.priority);
  const [models, setModels] = useState((provider.models ?? []).join(", "));

  const save = async () => {
    const patch: any = { id: provider.id, base_url: baseUrl, priority: Number(priority), models: models.split(",").map((m) => m.trim()).filter(Boolean) };
    if (apiKey.trim()) patch.api_key = apiKey.trim();
    await update.mutateAsync(patch);
    toast.success(`${provider.name} configured`);
    setApiKey("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong sm:max-w-md" data-testid="configure-provider-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">Configure {provider.name}</DialogTitle>
          <DialogDescription>Keys are encrypted at rest. Only a masked preview is ever returned.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>API Key {provider.configured && <span className="text-xs text-muted-foreground">(current: {provider.api_key_masked})</span>}</Label>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={provider.configured ? "Enter to replace…" : "sk-…"} data-testid="provider-key-input" />
          </div>
          <div className="space-y-1.5"><Label>Base URL</Label><Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} /></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5"><Label>Priority</Label><Input type="number" value={priority} onChange={(e) => setPriority(Number(e.target.value))} /></div>
          </div>
          <div className="space-y-1.5"><Label>Models (comma-separated)</Label><Input value={models} onChange={(e) => setModels(e.target.value)} /></div>
          <div className="flex flex-wrap gap-1.5">
            {(provider.supported_features ?? []).map((f) => <Badge key={f} variant="outline" className="text-[10px]">{f}</Badge>)}
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={save} disabled={update.isPending} data-testid="provider-config-save">Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ProviderRow({ p }: { p: Provider }) {
  const update = useUpdateProvider();
  const del = useDeleteProvider();
  const test = useTestProvider();
  const [configOpen, setConfigOpen] = useState(false);

  const runTest = async () => {
    const res = await test.mutateAsync(p.id);
    if (res.status === "ready") toast.success(res.message);
    else toast.error(res.message);
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card/50 px-4 py-3" data-testid={`provider-row-${p.id}`}>
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary"><Cpu className="h-4 w-4 text-primary" /></div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{p.name}</p>
          {p.is_default && <Badge className="gap-1 bg-primary/15 text-primary hover:bg-primary/15"><Star className="h-3 w-3" /> Default</Badge>}
          <StatusBadge status={p.status} />
          <span className="text-xs text-muted-foreground">Priority {p.priority}</span>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {p.api_key_masked ? `Key ${p.api_key_masked} · ` : ""}{p.models?.length ? p.models.join(", ") : p.base_url || "Not configured"}
        </p>
      </div>

      <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setConfigOpen(true)} data-testid={`provider-configure-${p.id}`}>
        <KeyRound className="h-3.5 w-3.5" /> Configure
      </Button>
      <Button size="sm" variant="ghost" className="gap-1.5" onClick={runTest} disabled={test.isPending} data-testid={`provider-test-${p.id}`}>
        {test.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plug className="h-3.5 w-3.5" />} Test
      </Button>
      {p.enabled && !p.is_default && (
        <Button size="sm" variant="ghost" className="gap-1.5 text-xs" onClick={async () => { await update.mutateAsync({ id: p.id, is_default: true }); toast.success(`${p.name} is now default`); }} data-testid={`provider-default-${p.id}`}>
          <Star className="h-3.5 w-3.5" /> Default
        </Button>
      )}
      <button className="text-muted-foreground hover:text-destructive" onClick={() => { del.mutate(p.id); toast.success(`${p.name} removed`); }} data-testid={`provider-delete-${p.id}`}>
        <Trash2 className="h-4 w-4" />
      </button>
      <Switch checked={p.enabled} data-testid={`provider-toggle-${p.id}`}
        onCheckedChange={async (v) => { await update.mutateAsync({ id: p.id, enabled: v }); toast.success(`${p.name} ${v ? "enabled" : "disabled"}`); }} />

      <ConfigureDialog provider={p} open={configOpen} onOpenChange={setConfigOpen} />
    </div>
  );
}

function AddProviderDialog({ categories }: { categories: any[] }) {
  const create = useCreateProvider();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("llm");
  const [baseUrl, setBaseUrl] = useState("");

  const submit = async () => {
    if (!name.trim()) return toast.error("Name required");
    await create.mutateAsync({ name: name.trim(), category, base_url: baseUrl });
    toast.success(`${name} added`); setName(""); setBaseUrl(""); setOpen(false);
  };

  return (
    <>
      <Button variant="outline" className="gap-2" onClick={() => setOpen(true)} data-testid="add-provider-btn"><Plus className="h-4 w-4" /> Add provider</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="glass-strong sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display text-xl">Add a provider</DialogTitle>
            <DialogDescription>Register any provider. Adapters validate keys without hardcoding names.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5"><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} data-testid="new-provider-name" /></div>
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger data-testid="new-provider-category"><SelectValue /></SelectTrigger>
                <SelectContent>{categories.map((c) => <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5"><Label>Base URL (optional)</Label><Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} /></div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={submit} disabled={create.isPending} data-testid="new-provider-save">Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function AIProviders() {
  const { data: providers = [] } = useProviders();
  const { data: categories = [] } = useProviderCategories();

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-bold">Provider Hub</h2>
          <p className="mt-1 text-sm text-muted-foreground">Adapter-based, provider-independent. Encrypted keys, connection testing, priority & defaults.</p>
        </div>
        <AddProviderDialog categories={categories} />
      </div>

      {categories.map((cat: any) => {
        const items = providers.filter((p) => p.category === cat.id);
        return (
          <section key={cat.id} data-testid={`provider-category-${cat.id}`}>
            <div className="mb-3 flex flex-wrap items-baseline gap-3">
              <h3 className="font-heading text-sm font-bold uppercase tracking-wide">{cat.label}</h3>
              <div className="flex flex-wrap gap-1">
                {cat.features?.map((f: string) => <span key={f} className="text-[10px] text-muted-foreground">#{f}</span>)}
              </div>
            </div>
            {items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-xs text-muted-foreground">
                No {cat.label.toLowerCase()} providers. Add one above.
              </div>
            ) : (
              <div className="space-y-2">{items.map((p) => <ProviderRow key={p.id} p={p} />)}</div>
            )}
          </section>
        );
      })}
    </div>
  );
}
