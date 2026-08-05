import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { CampaignManager, PublishingQueue, PublishCalendar } from "@/features/publish/PublishPro";

export default function PublishForge() {
  const mod = getModule("publish-forge");
  return (
    <ModuleShell
      module={mod}
      requireProject={false}
      content={{
        channels: <CampaignManager />,
        releases: <PublishingQueue />,
        schedule: <PublishCalendar />,
      }}
    />
  );
}
