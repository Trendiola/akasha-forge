import { Blocks, Code2, ShieldCheck } from "lucide-react";
import { getModule } from "@/config/modules";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";

export default function PluginForge() {
  const module = getModule("plugin-forge");
  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader icon={module.icon} title={module.label} tagline={module.tagline} description={module.description} accent={module.accent} />
      <div className="mb-5 grid gap-3 md:grid-cols-3">
        {[
          [ShieldCheck, "Isolated by design", "Extensions are never assumed installed or trusted."],
          [Code2, "Developer surface", "Installation will appear when a signed package workflow is available."],
          [Blocks, "Installed plugins", "0 detected in this clean workspace."],
        ].map(([Icon, title, copy]: any) => (
          <div key={title} className="akasha-card p-4"><Icon className="mb-3 h-5 w-5 text-slate-400" /><h2 className="text-sm font-semibold">{title}</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">{copy}</p></div>
        ))}
      </div>
      <EmptyState icon={Blocks} accent={module.accent} title="No plugins installed" description="No sample extensions have been added. Plugin installation remains unavailable until a verified package, permission and sandbox workflow is present." />
    </div>
  );
}
