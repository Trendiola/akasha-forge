import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { ProviderRequired } from "@/components/forge/ProviderRequired";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useForgeItems } from "@/features/forge/hooks";
import { MovieStudio } from "./MovieStudio";

export default function VideoForge() {
  const mod = getModule("video-forge");
  const project = useActiveProject();
  const { data: scenes = [] } = useForgeItems(project?.id, "video", "scene");
  const sceneOptions = scenes.map((s) => ({ value: s.id, label: s.title }));

  const tabs: ForgeTab[] = [
    { id: "studio", label: "Movie Studio", custom: <MovieStudio /> },
    { id: "scenes", label: "Scenes", schema: { kind: "scene", singular: "Scene", titleField: "title", fields: [
      { name: "title", label: "Scene title", type: "text", required: true },
      { name: "description", label: "Description", type: "textarea" },
      { name: "duration", label: "Duration (sec)", type: "number", placeholder: "30" },
    ] } },
    { id: "shots", label: "Shots", schema: { kind: "shot", singular: "Shot", titleField: "title", fields: [
      { name: "title", label: "Shot title", type: "text", required: true },
      { name: "scene", label: "Scene", type: "select", options: sceneOptions },
      { name: "description", label: "Description", type: "textarea" },
      { name: "camera_notes", label: "Camera notes", type: "textarea", placeholder: "Lens, movement, framing…" },
      { name: "duration", label: "Duration (sec)", type: "number" },
    ] } },
    { id: "renders", label: "Render Queue",
      banner: <ProviderRequired category="video" action="video rendering" />,
      schema: { kind: "render_job", singular: "Render Job", titleField: "title", fields: [
        { name: "title", label: "Job name", type: "text", required: true },
        { name: "status", label: "Status", type: "select", options: [
          { value: "queued", label: "Queued" }, { value: "processing", label: "Processing" }, { value: "done", label: "Done" },
        ] },
      ] } },
  ];
  return <ForgeWorkspace module={mod} moduleKey="video" tabs={tabs} />;
}
