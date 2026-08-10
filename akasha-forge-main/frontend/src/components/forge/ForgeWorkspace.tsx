import React, { useState } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2 } from "lucide-react";
import type { ModuleDef } from "@/config/modules";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useForgeItems, useCreateForgeItem, useUpdateForgeItem, useDeleteForgeItem, type ForgeItem } from "@/features/forge/hooks";
import { ItemFormModal, type ForgeSchema } from "./ItemFormModal";

export interface ForgeTab {
  id: string;
  label: string;
  schema?: ForgeSchema;      // crud tab
  custom?: React.ReactNode;  // custom tab (bible / canvas / etc.)
  banner?: React.ReactNode;  // e.g. ProviderRequired
}

interface Props {
  module: ModuleDef;
  moduleKey: string;
  tabs: ForgeTab[];
  activeTab?: string;
  onTabChange?: (v: string) => void;
}

function CrudTab({ moduleKey, schema, accent }: { moduleKey: string; schema: ForgeSchema; accent: string }) {
  const project = useActiveProject();
  const { data: items = [], isLoading } = useForgeItems(project?.id, moduleKey, schema.kind);
  const create = useCreateForgeItem(project?.id ?? "", moduleKey);
  const update = useUpdateForgeItem(project?.id ?? "", moduleKey);
  const del = useDeleteForgeItem(project?.id ?? "", moduleKey);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ForgeItem | null>(null);

  const openNew = () => { setEditing(null); setModalOpen(true); };
  const openEdit = (item: ForgeItem) => { setEditing(item); setModalOpen(true); };

  const onSubmit = async ({ title, data }: { title: string; data: Record<string, any> }) => {
    if (editing) {
      await update.mutateAsync({ id: editing.id, title, data });
      toast.success(`${schema.singular} updated`);
    } else {
      await create.mutateAsync({ kind: schema.kind, title, data });
      toast.success(`${schema.singular} created`);
    }
  };

  const preview = (item: ForgeItem) =>
    schema.fields
      .filter((f) => f.name !== schema.titleField && item.data[f.name] !== undefined && item.data[f.name] !== "" && f.type !== "switch")
      .slice(0, 2)
      .map((f) => String(item.data[f.name]))
      .join(" · ");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{items.length} {schema.singular.toLowerCase()}{items.length === 1 ? "" : "s"}</p>
        <Button size="sm" className="gap-1.5" style={{ background: accent }} onClick={openNew} data-testid={`forge-new-${schema.kind}`}>
          <Plus className="h-4 w-4" /> New {schema.singular}
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="h-24 animate-pulse rounded-xl border border-border bg-card/40" />)}</div>
      ) : items.length === 0 ? (
        <EmptyState icon={Plus} accent={accent} title={`No ${schema.singular.toLowerCase()}s yet`}
          description={`Create your first ${schema.singular.toLowerCase()}. It saves instantly and stays after refresh.`}
          action={<Button className="gap-2" style={{ background: accent }} onClick={openNew}><Plus className="h-4 w-4" /> New {schema.singular}</Button>} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div key={item.id} className="group flex flex-col rounded-xl border border-border bg-card/60 p-4 transition-colors hover:border-primary/40" data-testid={`forge-item-${item.id}`}>
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0 flex-1 truncate font-heading font-semibold">{item.title}</p>
                <div className="flex shrink-0 gap-1 opacity-60 transition-opacity group-hover:opacity-100">
                  <button onClick={() => openEdit(item)} className="text-muted-foreground hover:text-primary focus-visible:text-primary" data-testid={`forge-edit-${item.id}`}><Pencil className="h-3.5 w-3.5" /></button>
                  <button onClick={() => { del.mutate(item.id); toast.success(`${schema.singular} deleted`); }} className="text-muted-foreground hover:text-destructive focus-visible:text-destructive" data-testid={`forge-delete-${item.id}`}><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
              {preview(item) && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{preview(item)}</p>}
            </div>
          ))}
        </div>
      )}

      <ItemFormModal open={modalOpen} onOpenChange={setModalOpen} schema={schema} accent={accent}
        initial={editing ? { id: editing.id, title: editing.title, data: editing.data } : null} onSubmit={onSubmit} />
    </div>
  );
}

export function ForgeWorkspace({ module, moduleKey, tabs, activeTab, onTabChange }: Props) {
  const project = useActiveProject();
  const first = tabs[0];
  const controlled = activeTab !== undefined;

  return (
    <div className="animate-in fade-in duration-500" data-testid={`module-${module.id}`}>
      <PageHeader icon={module.icon} title={module.label} tagline={module.tagline} description={module.description} accent={module.accent} />

      {!project ? (
        <EmptyState icon={module.icon} accent={module.accent} title="Select a project"
          description={`${module.label} works within a project. Choose or create one to begin.`} />
      ) : (
        <Tabs
          {...(controlled ? { value: activeTab, onValueChange: onTabChange } : { defaultValue: first?.id })}
          className="w-full"
        >
          <TabsList className="mb-6 h-auto flex-wrap justify-start gap-1 bg-secondary/40 p-1">
            {tabs.map((t) => (
              <TabsTrigger key={t.id} value={t.id} className="rounded-md px-4 py-1.5 text-sm data-[state=active]:bg-background" data-testid={`${module.id}-tab-${t.id}`}>{t.label}</TabsTrigger>
            ))}
          </TabsList>
          {tabs.map((t) => (
            <TabsContent key={t.id} value={t.id} className="mt-0">
              {t.banner}
              {t.schema ? <CrudTab moduleKey={moduleKey} schema={t.schema} accent={module.accent} /> : t.custom}
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}
