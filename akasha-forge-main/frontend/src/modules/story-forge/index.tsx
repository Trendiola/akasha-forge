import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function StoryForge() {
  const mod = getModule("story-forge");
  const project = useActiveProject();
  const tabs: ForgeTab[] = [
    { id: "bible", label: "Story Bible", custom: <BibleEditor projectId={project?.id} type="story" accent={mod.accent} /> },
    { id: "chapters", label: "Chapters", schema: { kind: "chapter", singular: "Chapter", titleField: "title", fields: [
      { name: "title", label: "Title", type: "text", required: true, placeholder: "Chapter title" },
      { name: "act", label: "Act", type: "text", placeholder: "e.g. Act I" },
      { name: "summary", label: "Summary", type: "textarea", placeholder: "What happens in this chapter?" },
    ] } },
    { id: "drafts", label: "Drafts", schema: { kind: "draft", singular: "Draft", titleField: "title", fields: [
      { name: "title", label: "Title", type: "text", required: true },
      { name: "content", label: "Content", type: "textarea", placeholder: "Write your draft…" },
    ] } },
    { id: "beats", label: "Beat Sheet", schema: { kind: "beat", singular: "Beat", titleField: "title", fields: [
      { name: "title", label: "Beat", type: "text", required: true, placeholder: "e.g. Inciting Incident" },
      { name: "description", label: "Description", type: "textarea" },
    ] } },
  ];
  return <ForgeWorkspace module={mod} moduleKey="story" tabs={tabs} />;
}
