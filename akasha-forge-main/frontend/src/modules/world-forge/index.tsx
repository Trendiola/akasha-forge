import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { BibleEditor } from "@/components/bible/BibleEditor";
import { useActiveProject } from "@/features/projects/useActiveProject";

export default function WorldForge() {
  const mod = getModule("world-forge");
  const project = useActiveProject();
  const tabs: ForgeTab[] = [
    { id: "bible", label: "World Bible", custom: <BibleEditor projectId={project?.id} type="world" accent={mod.accent} /> },
    { id: "locations", label: "Locations", schema: { kind: "location", singular: "Location", titleField: "title", fields: [
      { name: "title", label: "Name", type: "text", required: true },
      { name: "region", label: "Region", type: "text" },
      { name: "description", label: "Description", type: "textarea" },
    ] } },
    { id: "factions", label: "Factions", schema: { kind: "faction", singular: "Faction", titleField: "title", fields: [
      { name: "title", label: "Name", type: "text", required: true },
      { name: "description", label: "Description", type: "textarea" },
    ] } },
    { id: "rules", label: "Rules", schema: { kind: "rule", singular: "Rule", titleField: "title", fields: [
      { name: "title", label: "Rule", type: "text", required: true },
      { name: "description", label: "Details", type: "textarea" },
    ] } },
    { id: "timeline", label: "Timeline", schema: { kind: "timeline_event", singular: "Event", titleField: "title", fields: [
      { name: "title", label: "Event", type: "text", required: true },
      { name: "date", label: "When", type: "text", placeholder: "e.g. Year 1042" },
      { name: "description", label: "Description", type: "textarea" },
    ] } },
  ];
  return <ForgeWorkspace module={mod} moduleKey="world" tabs={tabs} />;
}
