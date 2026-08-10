import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { ProviderRequired } from "@/components/forge/ProviderRequired";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function MusicForge() {
  const mod = getModule("music-forge");
  const project = useActiveProject();
  const tabs: ForgeTab[] = [
    {
      id: "briefs",
      label: "Music Briefs",
      banner: <ProviderRequired category="music" action="music generation" />,
      schema: {
        kind: "music_brief", singular: "Music Brief", titleField: "title",
        fields: [
          { name: "title", label: "Title", type: "text", required: true, placeholder: "e.g. Main Theme" },
          { name: "mood", label: "Mood", type: "text", placeholder: "Epic, melancholic" },
          { name: "genre", label: "Genre", type: "text", placeholder: "Orchestral" },
          { name: "tempo", label: "Tempo (BPM)", type: "number", placeholder: "120" },
          { name: "instruments", label: "Instruments", type: "textarea", placeholder: "Strings, brass, choir…" },
          { name: "duration", label: "Duration (sec)", type: "number", placeholder: "90" },
          { name: "loop", label: "Loopable", type: "switch" },
        ],
      },
    },
    { id: "themes", label: "Music Bible", custom: <BibleEditor projectId={project?.id} type="music" accent={mod.accent} /> },
  ];
  return <ForgeWorkspace module={mod} moduleKey="music" tabs={tabs} />;
}
