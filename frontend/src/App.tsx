import { BrowserRouter, HashRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AppProvider } from "@/store/app-context";
import { AppShell } from "@/components/layout/AppShell";
import { isDesktop } from "@/lib/runtime";

import AkashaCore from "@/modules/akasha-core";
import AkashaBrain from "@/modules/akasha-brain";
import StoryForge from "@/modules/story-forge";
import CharacterForge from "@/modules/character-forge";
import WorldForge from "@/modules/world-forge";
import ImageForge from "@/modules/image-forge";
import VideoForge from "@/modules/video-forge";
import VoiceForge from "@/modules/voice-forge";
import MusicForge from "@/modules/music-forge";
import LanguageForge from "@/modules/language-forge";
import WorkflowForge from "@/modules/workflow-forge";
import PublishForge from "@/modules/publish-forge";
import PluginForge from "@/modules/plugin-forge";
import ProviderHub from "@/modules/provider-hub";
import Assets from "@/pages/Assets";
import ProjectsPage from "@/pages/ProjectsPage";
import Settings from "@/pages/settings/Settings";

export default function App() {
  // Packaged desktop shells load over a non-server origin where deep-link
  // refresh needs hash routing; the web preview keeps clean BrowserRouter URLs.
  const Router = isDesktop() ? HashRouter : BrowserRouter;
  return (
    <AppProvider>
      <Router>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<AkashaCore />} />
            <Route path="brain" element={<AkashaBrain />} />
            <Route path="story" element={<StoryForge />} />
            <Route path="character" element={<CharacterForge />} />
            <Route path="world" element={<WorldForge />} />
            <Route path="image" element={<ImageForge />} />
            <Route path="video" element={<VideoForge />} />
            <Route path="voice" element={<VoiceForge />} />
            <Route path="music" element={<MusicForge />} />
            <Route path="language" element={<LanguageForge />} />
            <Route path="workflow" element={<WorkflowForge />} />
            <Route path="publish" element={<PublishForge />} />
            <Route path="plugins" element={<PluginForge />} />
            <Route path="providers" element={<ProviderHub />} />
            <Route path="assets" element={<Assets />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="settings/*" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
      <Toaster position="bottom-right" theme="dark" />
    </AppProvider>
  );
}
