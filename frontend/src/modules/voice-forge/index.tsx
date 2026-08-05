import { ForgeWorkspace, type ForgeTab } from "@/components/forge/ForgeWorkspace";
import { getModule } from "@/config/modules";
import { ProviderRequired } from "@/components/forge/ProviderRequired";
import { useProviders } from "@/features/providers/hooks";

export default function VoiceForge() {
  const mod = getModule("voice-forge");
  const { data: providers = [] } = useProviders("voice");
  const providerOptions = providers.map((p) => ({ value: p.id, label: p.name }));

  const tabs: ForgeTab[] = [
    {
      id: "voices",
      label: "Voice Profiles",
      banner: <ProviderRequired category="voice" action="voice synthesis" />,
      schema: {
        kind: "voice_profile", singular: "Voice Profile", titleField: "title",
        fields: [
          { name: "title", label: "Name", type: "text", required: true, placeholder: "e.g. Narrator — Kael" },
          { name: "language", label: "Language", type: "text", placeholder: "English" },
          { name: "accent", label: "Accent", type: "text", placeholder: "British" },
          { name: "style", label: "Style", type: "text", placeholder: "Warm, cinematic" },
          { name: "provider", label: "Provider", type: "select", options: providerOptions },
          { name: "voice_id", label: "Voice ID", type: "text", placeholder: "Provider voice id" },
        ],
      },
    },
  ];
  return <ForgeWorkspace module={mod} moduleKey="voice" tabs={tabs} />;
}
