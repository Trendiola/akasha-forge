import { useState } from "react";
import { toast } from "sonner";
import { Trash2, ImageOff, Images, Plus, MonitorPlay, FolderPlus } from "lucide-react";
import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { ImageEditor } from "@/features/imageEdit/ImageEditor";
import { ImageForgeProvider, useImageForge } from "@/features/imageEdit/ImageForgeContext";
import { EmptyState } from "@/components/common/EmptyState";
import { fileUrl } from "@/lib/api";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useCreateForgeItem, useDeleteForgeItem, type ForgeItem } from "@/features/forge/hooks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel } from "@/components/ui/dropdown-menu";

function AssetGallery({ accent }: { accent: string }) {
  const { projectId, assets, galleries, openOnCanvas, addToGallery } = useImageForge();
  const del = useDeleteForgeItem(projectId ?? "", "image");

  if (assets.length === 0) {
    return <EmptyState icon={ImageOff} accent={accent} title="No assets yet" description="Uploaded and generated images are stored here automatically." />;
  }
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4" data-testid="asset-gallery">
      {assets.map((a) => (
        <div key={a.id} className="group relative overflow-hidden rounded-xl border border-border bg-card/50" data-testid={`asset-${a.id}`}>
          <div className="flex aspect-square items-center justify-center bg-secondary/40">
            {a.data.file_id ? <img src={fileUrl(a.data.file_id)} alt={a.title} className="h-full w-full object-cover" /> : <Badge variant="outline" className="text-[10px]">{a.data.status ?? "queued"}</Badge>}
          </div>
          <div className="flex items-center justify-between px-2 py-1.5">
            <span className="truncate text-xs">{a.title}</span>
            <button onClick={() => { del.mutate(a.id); toast.success("Asset removed"); }} className="text-muted-foreground hover:text-destructive" data-testid={`asset-delete-${a.id}`}><Trash2 className="h-3.5 w-3.5" /></button>
          </div>
          <div className="flex items-center gap-1.5 border-t border-border px-2 py-1.5">
            {a.data.file_id && (
              <Button size="sm" variant="ghost" className="h-7 flex-1 gap-1 px-1.5 text-[11px]" onClick={() => openOnCanvas(a.id)} data-testid={`asset-open-canvas-${a.id}`}>
                <MonitorPlay className="h-3 w-3" /> Canvas
              </Button>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost" className="h-7 flex-1 gap-1 px-1.5 text-[11px]" data-testid={`asset-add-gallery-${a.id}`}>
                  <FolderPlus className="h-3 w-3" /> Gallery
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>Add to gallery</DropdownMenuLabel>
                {galleries.length === 0 ? (
                  <DropdownMenuItem disabled>No galleries yet</DropdownMenuItem>
                ) : (
                  galleries.map((g) => (
                    <DropdownMenuItem key={g.id} onClick={() => addToGallery(g.id, a.id)} data-testid={`asset-${a.id}-gallery-option-${g.id}`}>{g.title}</DropdownMenuItem>
                  ))
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      ))}
    </div>
  );
}

function GalleriesView({ accent }: { accent: string }) {
  const { projectId, assets, galleries } = useImageForge();
  const create = useCreateForgeItem(projectId ?? "", "image");
  const del = useDeleteForgeItem(projectId ?? "", "image");
  const [name, setName] = useState("");

  const assetById = (id: string): ForgeItem | undefined => assets.find((a) => a.id === id);

  const addGallery = async () => {
    if (!name.trim()) return;
    try {
      await create.mutateAsync({ kind: "gallery", title: name.trim(), data: { asset_ids: [] } });
      setName("");
      toast.success("Gallery created");
    } catch { toast.error("Could not create gallery. Please try again."); }
  };

  return (
    <div className="space-y-5" data-testid="galleries-view">
      <div className="flex gap-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New gallery name…" data-testid="gallery-name-input" onKeyDown={(e) => e.key === "Enter" && addGallery()} />
        <Button className="gap-1.5" style={{ background: accent }} onClick={addGallery} data-testid="gallery-create-btn"><Plus className="h-4 w-4" /> Create</Button>
      </div>

      {galleries.length === 0 ? (
        <EmptyState icon={Images} accent={accent} title="No galleries yet" description="Create a gallery, then add images to it from the Canvas or Assets tab." />
      ) : (
        <div className="space-y-5">
          {galleries.map((g) => {
            const ids: string[] = Array.isArray(g.data?.asset_ids) ? g.data.asset_ids : [];
            const members = ids.map(assetById).filter(Boolean) as ForgeItem[];
            return (
              <div key={g.id} className="rounded-2xl border border-border bg-card/40 p-4" data-testid={`gallery-${g.id}`}>
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <p className="font-heading font-semibold">{g.title}</p>
                    <p className="text-xs text-muted-foreground">{members.length} image{members.length === 1 ? "" : "s"}</p>
                  </div>
                  <button onClick={() => { del.mutate(g.id); toast.success("Gallery deleted"); }} className="text-muted-foreground hover:text-destructive" data-testid={`gallery-delete-${g.id}`}><Trash2 className="h-4 w-4" /></button>
                </div>
                {members.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">Empty — add images from Canvas or Assets.</p>
                ) : (
                  <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
                    {members.map((m) => (
                      <div key={m.id} className="overflow-hidden rounded-lg border border-border bg-secondary/40" data-testid={`gallery-${g.id}-member-${m.id}`}>
                        <div className="flex aspect-square items-center justify-center">
                          {m.data.file_id ? <img src={fileUrl(m.data.file_id)} alt={m.title} className="h-full w-full object-cover" /> : <Badge variant="outline" className="text-[10px]">{m.data.status ?? "queued"}</Badge>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ImageForgeInner({ mod }: { mod: ReturnType<typeof getModule> }) {
  const [tab, setTab] = useState("canvas");
  const project = useActiveProject();
  const tabs: ForgeTab[] = [
    { id: "canvas", label: "Canvas", custom: <ImageEditor accent={mod.accent} /> },
    { id: "gallery", label: "Galleries", custom: <GalleriesView accent={mod.accent} /> },
    { id: "assets", label: "Assets", custom: <AssetGallery accent={mod.accent} /> },
  ];
  return (
    <ImageForgeProvider projectId={project?.id} onSwitchTab={setTab}>
      <ForgeWorkspace module={mod} moduleKey="image" tabs={tabs} activeTab={tab} onTabChange={setTab} />
    </ImageForgeProvider>
  );
}

export default function ImageForge() {
  const mod = getModule("image-forge");
  return <ImageForgeInner mod={mod} />;
}
