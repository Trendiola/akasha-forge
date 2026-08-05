import { toast } from "sonner";
import { Trash2, ImageOff } from "lucide-react";
import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { ImageEditor } from "@/features/imageEdit/ImageEditor";
import { EmptyState } from "@/components/common/EmptyState";
import { fileUrl } from "@/lib/api";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useForgeItems, useDeleteForgeItem } from "@/features/forge/hooks";
import { Badge } from "@/components/ui/badge";

function AssetGallery({ accent }: { accent: string }) {
  const project = useActiveProject();
  const { data: assets = [] } = useForgeItems(project?.id, "image", "asset");
  const del = useDeleteForgeItem(project?.id ?? "", "image");

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
            <button onClick={() => { del.mutate(a.id); toast.success("Asset removed"); }} className="text-muted-foreground hover:text-destructive"><Trash2 className="h-3.5 w-3.5" /></button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ImageForge() {
  const mod = getModule("image-forge");
  const project = useActiveProject();
  const tabs: ForgeTab[] = [
    { id: "canvas", label: "Canvas", custom: <ImageEditor projectId={project?.id} accent={mod.accent} /> },
    { id: "gallery", label: "Galleries", schema: { kind: "gallery", singular: "Gallery", titleField: "title", fields: [
      { name: "title", label: "Gallery name", type: "text", required: true },
      { name: "description", label: "Description", type: "textarea" },
    ] } },
    { id: "assets", label: "Assets", custom: <AssetGallery accent={mod.accent} /> },
  ];
  return <ForgeWorkspace module={mod} moduleKey="image" tabs={tabs} />;
}
