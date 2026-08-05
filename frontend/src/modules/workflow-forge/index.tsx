import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Save, Workflow as WorkflowIcon, GitBranch, Link2 } from "lucide-react";
import { getModule } from "@/config/modules";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useForgeItems, useCreateForgeItem, useUpdateForgeItem, useDeleteForgeItem, type ForgeItem } from "@/features/forge/hooks";
import { cn } from "@/lib/utils";

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
const NODE_TYPES = ["input", "process", "output"];
const NODE_COLOR: Record<string, string> = { input: "#22C55E", process: "#6D3BFF", output: "#0EA5E9" };

export default function WorkflowForge() {
  const mod = getModule("workflow-forge");
  const project = useActiveProject();
  const { data: flows = [] } = useForgeItems(project?.id, "workflow", "workflow");
  const create = useCreateForgeItem(project?.id ?? "", "workflow");
  const update = useUpdateForgeItem(project?.id ?? "", "workflow");
  const del = useDeleteForgeItem(project?.id ?? "", "workflow");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [nodeName, setNodeName] = useState("");
  const [nodeType, setNodeType] = useState("process");
  const [edgeFrom, setEdgeFrom] = useState("");
  const [edgeTo, setEdgeTo] = useState("");

  const selected = flows.find((f) => f.id === selectedId) ?? null;
  useEffect(() => {
    if (selected) setDraft({ nodes: selected.data.nodes ?? [], edges: selected.data.edges ?? [] });
  }, [selectedId]); // eslint-disable-line

  const newFlow = async () => {
    if (!name.trim()) return toast.error("Workflow name required");
    const f = await create.mutateAsync({ kind: "workflow", title: name.trim(), data: { nodes: [], edges: [] } });
    setName(""); setSelectedId(f.id);
    toast.success("Workflow created");
  };

  const save = async () => {
    if (!selected) return;
    await update.mutateAsync({ id: selected.id, data: { nodes: draft.nodes, edges: draft.edges } });
    toast.success("Workflow saved");
  };

  const rename = async (f: ForgeItem, title: string) => {
    await update.mutateAsync({ id: f.id, title });
  };

  const addNode = () => {
    if (!nodeName.trim()) return;
    setDraft((d) => ({ ...d, nodes: [...d.nodes, { id: uid(), name: nodeName.trim(), type: nodeType }] }));
    setNodeName("");
  };
  const addEdge = () => {
    if (!edgeFrom || !edgeTo || edgeFrom === edgeTo) return toast.error("Pick two different nodes");
    setDraft((d) => ({ ...d, edges: [...d.edges, { id: uid(), from: edgeFrom, to: edgeTo }] }));
    setEdgeFrom(""); setEdgeTo("");
  };
  const nodeName_ = (id: string) => draft.nodes.find((n) => n.id === id)?.name ?? "?";

  return (
    <div className="animate-in fade-in duration-500" data-testid="module-workflow-forge">
      <PageHeader icon={mod.icon} title={mod.label} tagline={mod.tagline} description={mod.description} accent={mod.accent} />

      {!project ? (
        <EmptyState icon={WorkflowIcon} accent={mod.accent} title="Select a project" description="Workflows are saved per project." />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">
          {/* Workflow list */}
          <div className="space-y-3">
            <div className="flex gap-2">
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New workflow…" data-testid="workflow-name-input"
                onKeyDown={(e) => { if (e.key === "Enter") newFlow(); }} />
              <Button size="icon" style={{ background: mod.accent }} onClick={newFlow} data-testid="workflow-create-btn"><Plus className="h-4 w-4" /></Button>
            </div>
            {flows.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">No workflows yet</p>
            ) : flows.map((f) => (
              <div key={f.id} onClick={() => setSelectedId(f.id)} data-testid={`workflow-item-${f.id}`}
                className={cn("flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 transition-colors", selectedId === f.id ? "border-primary bg-primary/10" : "border-border bg-card/50 hover:border-primary/40")}>
                <GitBranch className="h-4 w-4" style={{ color: mod.accent }} />
                <span className="flex-1 truncate text-sm font-medium">{f.title}</span>
                <button onClick={(e) => { e.stopPropagation(); del.mutate(f.id); if (selectedId === f.id) setSelectedId(null); toast.success("Workflow deleted"); }}
                  className="text-muted-foreground hover:text-destructive" data-testid={`workflow-delete-${f.id}`}><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>

          {/* Editor */}
          {!selected ? (
            <EmptyState icon={WorkflowIcon} accent={mod.accent} title="Select or create a workflow" description="Add nodes and connect them, then save. The graph persists in MongoDB." />
          ) : (
            <div className="space-y-5">
              <div className="flex items-center gap-2">
                <Input defaultValue={selected.title} onBlur={(e) => rename(selected, e.target.value)} className="max-w-sm font-heading font-semibold" data-testid="workflow-rename-input" />
                <Button className="ml-auto gap-1.5" style={{ background: mod.accent }} onClick={save} data-testid="workflow-save-btn"><Save className="h-4 w-4" /> Save</Button>
              </div>

              {/* Nodes */}
              <div className="rounded-2xl border border-border bg-card/50 p-4">
                <p className="mb-3 font-heading text-sm font-bold">Nodes</p>
                <div className="mb-3 flex gap-2">
                  <Input value={nodeName} onChange={(e) => setNodeName(e.target.value)} placeholder="Node name" className="flex-1" data-testid="node-name-input" onKeyDown={(e) => { if (e.key === "Enter") addNode(); }} />
                  <Select value={nodeType} onValueChange={setNodeType}>
                    <SelectTrigger className="w-36" data-testid="node-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{NODE_TYPES.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}</SelectContent>
                  </Select>
                  <Button variant="outline" className="gap-1.5" onClick={addNode} data-testid="node-add-btn"><Plus className="h-4 w-4" /> Add</Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {draft.nodes.length === 0 && <p className="text-xs text-muted-foreground">No nodes yet.</p>}
                  {draft.nodes.map((n) => (
                    <Badge key={n.id} variant="outline" className="gap-1.5 py-1" style={{ borderColor: `${NODE_COLOR[n.type]}66` }} data-testid={`node-${n.id}`}>
                      <span className="h-2 w-2 rounded-full" style={{ background: NODE_COLOR[n.type] }} />
                      {n.name}
                      <button onClick={() => setDraft((d) => ({ nodes: d.nodes.filter((x) => x.id !== n.id), edges: d.edges.filter((e) => e.from !== n.id && e.to !== n.id) }))}><Trash2 className="h-3 w-3" /></button>
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Connections */}
              <div className="rounded-2xl border border-border bg-card/50 p-4">
                <p className="mb-3 font-heading text-sm font-bold">Connections</p>
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Select value={edgeFrom} onValueChange={setEdgeFrom}>
                    <SelectTrigger className="w-40" data-testid="edge-from-select"><SelectValue placeholder="From" /></SelectTrigger>
                    <SelectContent>{draft.nodes.map((n) => <SelectItem key={n.id} value={n.id}>{n.name}</SelectItem>)}</SelectContent>
                  </Select>
                  <Link2 className="h-4 w-4 text-muted-foreground" />
                  <Select value={edgeTo} onValueChange={setEdgeTo}>
                    <SelectTrigger className="w-40" data-testid="edge-to-select"><SelectValue placeholder="To" /></SelectTrigger>
                    <SelectContent>{draft.nodes.map((n) => <SelectItem key={n.id} value={n.id}>{n.name}</SelectItem>)}</SelectContent>
                  </Select>
                  <Button variant="outline" className="gap-1.5" onClick={addEdge} data-testid="edge-add-btn"><Plus className="h-4 w-4" /> Connect</Button>
                </div>
                <div className="space-y-1.5">
                  {draft.edges.length === 0 && <p className="text-xs text-muted-foreground">No connections yet.</p>}
                  {draft.edges.map((e) => (
                    <div key={e.id} className="flex items-center gap-2 rounded-lg border border-border bg-background/40 px-3 py-1.5 text-sm" data-testid={`edge-${e.id}`}>
                      <span>{nodeName_(e.from)}</span><span className="text-muted-foreground">→</span><span>{nodeName_(e.to)}</span>
                      <button onClick={() => setDraft((d) => ({ ...d, edges: d.edges.filter((x) => x.id !== e.id) }))} className="ml-auto text-muted-foreground hover:text-destructive"><Trash2 className="h-3.5 w-3.5" /></button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
