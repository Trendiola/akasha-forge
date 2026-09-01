import { useProviders } from "@/features/providers/hooks";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export function AiStatus() {
  const { data: providers = [] } = useProviders();
  const enabled = providers.filter((p) => p.enabled && p.configured);
  const ready = enabled.filter((p) => p.status === "ready");
  const online = ready.length > 0;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          data-testid="ai-status"
          className="flex items-center gap-2 rounded-full border border-border bg-secondary/50 px-3 py-1.5 text-xs transition-colors hover:border-primary/40"
        >
          <span className="relative flex h-2 w-2">
            <span
              className={cn(
                "absolute inline-flex h-full w-full rounded-full opacity-75",
                online && "animate-ping bg-emerald-400"
              )}
            />
            <span
              className={cn(
                "relative inline-flex h-2 w-2 rounded-full",
                online ? "bg-emerald-400" : "bg-muted-foreground"
              )}
            />
          </span>
          <span className="text-muted-foreground">AI</span>
          <span className="font-medium">{online ? `${ready.length} ready` : enabled.length ? "Unverified" : "Offline"}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Engine status
        </p>
        {enabled.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No providers enabled. Configure them in Settings → AI Providers.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {enabled.map((p) => (
              <li key={p.id} className="flex items-center justify-between text-sm">
                <span>{p.name}</span>
                <span className={cn("text-[10px] uppercase", p.status === "ready" ? "text-emerald-400" : "text-amber-300")}>{p.status}</span>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}
