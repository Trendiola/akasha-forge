import { useProviders } from "@/features/providers/hooks";
import type { ProviderCategory } from "@/types";
import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function ProviderRequired({ category, action }: { category: ProviderCategory; action: string }) {
  const { data: providers = [] } = useProviders(category);
  const ready = providers.some((p) => p.enabled);
  if (ready) return null;
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm" data-testid={`provider-required-${category}`}>
      <AlertTriangle className="h-4 w-4 text-amber-400" />
      <span className="text-amber-100/90">
        No {category} provider is enabled, so {action} is unavailable. You can still create and save records.
      </span>
      <Link to="/settings/providers" className="ml-auto">
        <Button size="sm" variant="outline" className="gap-1.5 border-amber-400/40">Configure provider</Button>
      </Link>
    </div>
  );
}
