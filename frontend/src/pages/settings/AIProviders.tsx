import { toast } from "sonner";
import { Cpu, Star, Plus } from "lucide-react";
import { useProviders, useUpdateProvider } from "@/features/providers/hooks";
import type { Provider, ProviderCategory } from "@/types";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/EmptyState";

const CATEGORIES: { id: ProviderCategory; label: string; hint: string }[] = [
  { id: "llm", label: "Language Models", hint: "Story, character & world generation" },
  { id: "image", label: "Image", hint: "Concept art & visuals" },
  { id: "video", label: "Video", hint: "Motion & scenes" },
  { id: "voice", label: "Voice", hint: "Dialogue & narration" },
  { id: "music", label: "Music", hint: "Score & soundtrack" },
  { id: "translation", label: "Translation", hint: "Localization" },
  { id: "publishing", label: "Publishing", hint: "Distribution channels" },
];

function ProviderRow({ p }: { p: Provider }) {
  const update = useUpdateProvider();

  return (
    <div
      className="flex items-center gap-4 rounded-xl border border-border bg-card/50 px-4 py-3"
      data-testid={`provider-row-${p.id}`}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary">
        <Cpu className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{p.name}</p>
          {p.is_default && (
            <Badge className="gap-1 bg-primary/15 text-primary hover:bg-primary/15">
              <Star className="h-3 w-3" /> Default
            </Badge>
          )}
          <Badge variant="outline" className="rounded-full text-[10px] uppercase">
            {p.kind}
          </Badge>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {p.models.length ? p.models.join(", ") : p.base_url || "Not configured"}
        </p>
      </div>

      {p.enabled && !p.is_default && (
        <Button
          size="sm"
          variant="ghost"
          className="gap-1.5 text-xs"
          data-testid={`provider-default-${p.id}`}
          onClick={async () => {
            await update.mutateAsync({ id: p.id, is_default: true });
            toast.success(`${p.name} set as default`);
          }}
        >
          <Star className="h-3.5 w-3.5" /> Make default
        </Button>
      )}

      <Switch
        checked={p.enabled}
        data-testid={`provider-toggle-${p.id}`}
        onCheckedChange={async (v) => {
          await update.mutateAsync({ id: p.id, enabled: v });
          toast.success(`${p.name} ${v ? "enabled" : "disabled"}`);
        }}
      />
    </div>
  );
}

export default function AIProviders() {
  const { data: providers = [] } = useProviders();

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-bold">AI Providers</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Pluggable engine architecture — every provider is replaceable and none are hardcoded.
          </p>
        </div>
        <Button variant="outline" className="gap-2" data-testid="add-provider-btn">
          <Plus className="h-4 w-4" /> Add provider
        </Button>
      </div>

      {CATEGORIES.map((cat) => {
        const items = providers.filter((p) => p.category === cat.id);
        return (
          <section key={cat.id} data-testid={`provider-category-${cat.id}`}>
            <div className="mb-3 flex items-baseline gap-3">
              <h3 className="font-heading text-sm font-bold uppercase tracking-wide">{cat.label}</h3>
              <span className="text-xs text-muted-foreground">{cat.hint}</span>
            </div>
            {items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-xs text-muted-foreground">
                No {cat.label.toLowerCase()} providers installed. Add one via Plugin Forge.
              </div>
            ) : (
              <div className="space-y-2">
                {items.map((p) => (
                  <ProviderRow key={p.id} p={p} />
                ))}
              </div>
            )}
          </section>
        );
      })}

      {providers.length === 0 && (
        <EmptyState icon={Cpu} title="No providers" description="Providers will appear here." />
      )}
    </div>
  );
}
