import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";

export default function LanguageForge() {
  const module = getModule("language-forge");
  const tabs: ForgeTab[] = [
    { id: "locales", label: "Locales", schema: { kind: "locale", singular: "Locale", titleField: "title", fields: [
      { name: "title", label: "Language / locale", type: "text", required: true, placeholder: "e.g. Italian (it-IT)" },
      { name: "status", label: "Status", type: "select", options: [
        { value: "planned", label: "Planned" },
        { value: "in_progress", label: "In progress" },
        { value: "review", label: "Review" },
        { value: "complete", label: "Complete" },
      ] },
      { name: "notes", label: "Localization notes", type: "textarea" },
    ] } },
    { id: "glossary", label: "Glossary", schema: { kind: "glossary_term", singular: "Term", titleField: "title", fields: [
      { name: "title", label: "Source term", type: "text", required: true },
      { name: "translation", label: "Approved translation", type: "text" },
      { name: "context", label: "Context and usage", type: "textarea" },
    ] } },
    { id: "review", label: "Review", schema: { kind: "translation_review", singular: "Review item", titleField: "title", fields: [
      { name: "title", label: "Asset or passage", type: "text", required: true },
      { name: "locale", label: "Locale", type: "text" },
      { name: "notes", label: "Review notes", type: "textarea" },
    ] } },
  ];
  return <ForgeWorkspace module={module} moduleKey="language" tabs={tabs} />;
}
