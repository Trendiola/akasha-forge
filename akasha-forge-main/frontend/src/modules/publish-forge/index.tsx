import { useState } from "react";
import { ModuleShell } from "@/components/common/ModuleShell";
import { getModule } from "@/config/modules";
import { CampaignManager, PublishingQueue, PublishCalendar, SchedulerDialog } from "@/features/publish/PublishPro";

export default function PublishForge() {
  const mod = getModule("publish-forge");
  const [newPostOpen, setNewPostOpen] = useState(false);
  return (
    <>
      <ModuleShell
        module={mod}
        requireProject={false}
        onNew={() => setNewPostOpen(true)}
        content={{
          channels: <CampaignManager />,
          releases: <PublishingQueue />,
          schedule: <PublishCalendar />,
        }}
      />
      <SchedulerDialog open={newPostOpen} onOpenChange={setNewPostOpen} />
    </>
  );
}
