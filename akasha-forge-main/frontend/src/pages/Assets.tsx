import { Boxes, Image, Clapperboard, Mic, Music } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const KINDS = [
  { id: "all", label: "All", icon: Boxes },
  { id: "images", label: "Images", icon: Image },
  { id: "videos", label: "Videos", icon: Clapperboard },
  { id: "audio", label: "Audio", icon: Mic },
  { id: "music", label: "Music", icon: Music },
];

export default function Assets() {
  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader
        icon={Boxes}
        title="Assets"
        tagline="Library"
        description="Every image, video, voice take and track generated across your projects lives here."
      />
      <Tabs defaultValue="all">
        <TabsList className="mb-6 bg-secondary/40 p-1">
          {KINDS.map((k) => (
            <TabsTrigger key={k.id} value={k.id} className="gap-1.5 data-[state=active]:bg-background" data-testid={`assets-tab-${k.id}`}>
              <k.icon className="h-3.5 w-3.5" />
              {k.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {KINDS.map((k) => (
          <TabsContent key={k.id} value={k.id}>
            <EmptyState
              icon={k.icon}
              title={`No ${k.label.toLowerCase()} assets yet`}
              description="Assets you generate in the Forges will be collected and organized here automatically."
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
