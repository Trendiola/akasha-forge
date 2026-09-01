import { LayoutTemplate } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";

export default function TemplatesPage() {
  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader icon={LayoutTemplate} title="Templates" tagline="Library" description="Reusable creative structures will live here when explicitly saved or installed." accent="#38BDF8" />
      <EmptyState icon={LayoutTemplate} accent="#38BDF8" title="No templates available" description="This clean workspace contains no bundled or sample templates. Template creation will appear when a persistent workflow is available." />
    </div>
  );
}
