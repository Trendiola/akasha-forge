import { BrowserRouter, HashRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AppProvider } from "@/store/app-context";
import { AppShell } from "@/components/layout/AppShell";
import { isDesktop, getRuntimeConfig } from "@/lib/runtime";

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
import TemplatesPage from "@/pages/TemplatesPage";

export default function App() {
  // Packaged desktop shells load over a non-server origin where deep-link
  // refresh needs hash routing; the web preview keeps clean BrowserRouter URLs.
  const Router = isDesktop() ? HashRouter : BrowserRouter;

  // Desktop startup error (AF-DESKTOP-006): if the Tauri shell could not reach
  // the backend engine, show a clear message instead of a blank window.
  const startupError = getRuntimeConfig().startupError;
  if (startupError) {
    return (
      <div
        data-testid="desktop-startup-error"
        className="min-h-screen flex items-center justify-center bg-[#0a0a0f] text-center px-6"
      >
        <div className="max-w-md space-y-3">
          <h1 className="text-2xl font-semibold text-white">Akasha Forge couldn’t start</h1>
          <p className="text-sm text-white/60">{startupError}</p>
        </div>
      </div>
    );
  }

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
            <Route path="templates" element={<TemplatesPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="settings/*" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
      <Toaster position="bottom-right" theme="dark" />
    </AppProvider>
  );
}
