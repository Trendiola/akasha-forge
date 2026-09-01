import { Boxes, Image, Clapperboard, Mic, Music, FolderKanban } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useForgeItems } from "@/features/forge/hooks";
import { fileUrl } from "@/lib/api";

const KINDS = [
  { id: "all", label: "All", icon: Boxes }, { id: "images", label: "Images", icon: Image },
  { id: "videos", label: "Videos", icon: Clapperboard }, { id: "audio", label: "Audio", icon: Mic }, { id: "music", label: "Music", icon: Music },
];

export default function Assets() {
  const project = useActiveProject();
  const { data: images = [], isLoading } = useForgeItems(project?.id, "image", "asset");

  return <div className="animate-in fade-in duration-500">
    <PageHeader icon={Boxes} title="Assets" tagline="Library" description="Every image, video, voice take and track generated across your projects lives here." />
    {!project ? <EmptyState icon={FolderKanban} title="Select a project" description="The asset library follows your active project so creative files never cross workspace boundaries." action={<Button asChild><Link to="/projects">Choose project</Link></Button>} /> : <Tabs defaultValue="all">
      <TabsList className="mb-6 bg-secondary/40 p-1">{KINDS.map((kind) => <TabsTrigger key={kind.id} value={kind.id} className="gap-1.5 data-[state=active]:bg-background" data-testid={`assets-tab-${kind.id}`}><kind.icon className="h-3.5 w-3.5" />{kind.label}</TabsTrigger>)}</TabsList>
      {KINDS.map((kind) => <TabsContent key={kind.id} value={kind.id}>
        {(kind.id === "all" || kind.id === "images") && images.length ? <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">{images.map((asset) => <Link to="/image" key={asset.id} className="group overflow-hidden rounded-xl border border-border bg-card/50 transition-colors hover:border-primary/35">
          <div className="flex aspect-square items-center justify-center bg-secondary/40">{asset.data.file_id ? <img src={fileUrl(asset.data.file_id)} alt={asset.title} className="h-full w-full object-cover" /> : <Badge variant="outline">{asset.data.status ?? "queued"}</Badge>}</div>
          <div className="p-3"><p className="truncate text-sm font-medium">{asset.title}</p><p className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">Image Forge</p></div>
        </Link>)}</div> : isLoading && (kind.id === "all" || kind.id === "images") ? <div className="h-40 animate-pulse rounded-2xl bg-card/40" /> : <EmptyState icon={kind.icon} title={`No ${kind.label.toLowerCase()} assets yet`} description={kind.id === "all" || kind.id === "images" ? "Upload or generate an image in Image Forge and it will appear here." : `${kind.label} produced by its Forge will appear here when the module creates persisted assets.`} />}
      </TabsContent>)}
    </Tabs>}
  </div>;
}
