import { useState } from "react";
import { toast } from "sonner";
import { Plus, ChevronRight, ChevronDown, Trash2, Film } from "lucide-react";
import { useProduction, useCreateNode, useDeleteNode } from "@/features/production/hooks";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const CHILD: Record<string, string> = { act: "chapter", chapter: "scene", scene: "shot" };
const COLORS: Record<string, string> = { act: "#6D3BFF", chapter: "#A855F7", scene: "#EC4899", shot: "#F43F5E" };

interface FlatRow {
  node: any;
  depth: number;
}

// Iteratively flatten the tree (no recursive component — avoids babel plugin issues).
function flatten(tree: any[], collapsed: Record<string, boolean>): FlatRow[] {
  const rows: FlatRow[] = [];
  const stack: FlatRow[] = [...tree].reverse().map((n) => ({ node: n, depth: 0 }));
  while (stack.length) {
    const row = stack.pop()!;
    rows.push(row);
    if (!collapsed[row.node.id] && row.node.children?.length) {
      for (let i = row.node.children.length - 1; i >= 0; i--) {
        stack.push({ node: row.node.children[i], depth: row.depth + 1 });
      }
    }
  }
  return rows;
}

export function ProductionBoard({ projectId }: { projectId?: string | null }) {
  const { data, isLoading } = useProduction(projectId ?? undefined);
  const create = useCreateNode(projectId ?? "");
  const del = useDeleteNode(projectId ?? "");
  const [adding, setAdding] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  if (!projectId) return <EmptyState icon={Film} title="Select a project" description="Scene production is organized per project." />;
  if (isLoading) return <div className="h-40 animate-pulse rounded-2xl border border-border bg-card/40" />;

  const tree = data?.tree ?? [];
  const rows = flatten(tree, collapsed);

  const addNode = async (type: string, parentId: string | null) => {
    if (!title.trim()) return toast.error("Title required");
    await create.mutateAsync({ type, parent_id: parentId, title: title.trim() });
    setTitle(""); setAdding(null);
    toast.success(`${type} added`);
  };

  const addRow = (type: string, parentId: string | null, keyId: string, indent = 0) =>
    adding === keyId ? (
      <div className="flex items-center gap-2 py-1" style={{ marginLeft: indent }}>
        <Input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} placeholder={`New ${type} title`} className="h-8"
          onKeyDown={(e) => { if (e.key === "Enter") addNode(type, parentId); if (e.key === "Escape") setAdding(null); }} data-testid="production-title-input" />
        <Button size="sm" className="h-8" onClick={() => addNode(type, parentId)} data-testid="production-add-confirm">Add</Button>
        <Button size="sm" variant="ghost" className="h-8" onClick={() => setAdding(null)}>Cancel</Button>
      </div>
    ) : (
      <button onClick={() => { setAdding(keyId); setTitle(""); }} style={{ marginLeft: indent }}
        className="flex items-center gap-1.5 py-1 text-xs text-muted-foreground hover:text-primary" data-testid={`production-add-${type}`}>
        <Plus className="h-3.5 w-3.5" /> Add {type}
      </button>
    );

  return (
    <div className="space-y-3" data-testid="production-board">
      <p className="text-sm text-muted-foreground">Project → Acts → Chapters → Scenes → Shots · {data?.count ?? 0} nodes</p>
      {tree.length === 0 ? (
        <EmptyState icon={Film} title="Structure your production" description="Build the narrative hierarchy. Start by adding an Act."
          action={addRow("act", null, "root")} />
      ) : (
        <div className="rounded-2xl border border-border bg-card/40 p-4">
          {rows.map(({ node, depth }) => {
            const child = CHILD[node.type];
            const hasChildren = node.children?.length > 0;
            return (
              <div key={node.id} style={{ marginLeft: depth * 18 }} className="border-l border-border/60 pl-3">
                <div className="group flex items-center gap-2 py-1.5" data-testid="production-node">
                  {hasChildren || child ? (
                    <button onClick={() => setCollapsed((c) => ({ ...c, [node.id]: !c[node.id] }))} className="text-muted-foreground">
                      {collapsed[node.id] ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                  ) : (
                    <span className="w-4" />
                  )}
                  <span className="h-2 w-2 rounded-full" style={{ background: COLORS[node.type] }} />
                  <span className="font-medium">{node.title}</span>
                  <Badge variant="outline" className="text-[10px] capitalize">{node.type}</Badge>
                  <button onClick={() => del.mutate(node.id)} className="ml-auto text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100" data-testid={`production-delete-${node.id}`}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                {!collapsed[node.id] && child && (
                  <div>{addRow(child, node.id, `${node.id}-${child}`, 18)}</div>
                )}
              </div>
            );
          })}
          <div className="mt-2 border-t border-border/60 pt-2">{addRow("act", null, "root")}</div>
        </div>
      )}
    </div>
  );
}
