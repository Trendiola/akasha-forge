import {
  LayoutDashboard,
  BrainCircuit,
  BookOpen,
  Users,
  Globe2,
  Image,
  Clapperboard,
  Mic,
  Music,
  Languages,
  Workflow,
  Send,
  Blocks,
  Settings,
  FolderOpen,
  Boxes,
  type LucideIcon,
} from "lucide-react";
import type { ProviderCategory } from "@/types";

export interface ModuleTab {
  id: string;
  label: string;
}

export interface ModuleDef {
  id: string;
  label: string;
  path: string;
  icon: LucideIcon;
  tagline: string;
  description: string;
  category?: ProviderCategory;
  accent: string;
  tabs: ModuleTab[];
  capabilities: string[];
}

export const MODULES: ModuleDef[] = [
  {
    id: "akasha-core",
    label: "Akasha Core",
    path: "/",
    icon: LayoutDashboard,
    tagline: "Command center",
    description: "Your creative universe at a glance — projects, activity and the pulse of every Forge.",
    accent: "#6D3BFF",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "activity", label: "Activity" },
      { id: "insights", label: "Insights" },
    ],
    capabilities: ["Unified dashboard", "Cross-module search", "Recent activity"],
  },
  {
    id: "akasha-brain",
    label: "Akasha Brain",
    path: "/brain",
    icon: BrainCircuit,
    tagline: "AI command center",
    description: "The intelligence layer — prompt optimization, project context and a creative co-pilot.",
    accent: "#6D3BFF",
    tabs: [
      { id: "command", label: "Command Center" },
      { id: "optimizer", label: "Prompt Optimizer" },
      { id: "assistant", label: "Assistant" },
    ],
    capabilities: ["Prompt Optimizer", "Context Engine", "Creative co-pilot"],
  },
  {
    id: "story-forge",
    label: "Story Forge",
    path: "/story",
    icon: BookOpen,
    tagline: "Narrative engine",
    description: "Build the Story Bible — arcs, chapters, beats and lore that anchor your world.",
    category: "llm",
    accent: "#8B5CF6",
    tabs: [
      { id: "bible", label: "Story Bible" },
      { id: "outline", label: "Outline" },
      { id: "drafts", label: "Drafts" },
      { id: "notes", label: "Notes" },
    ],
    capabilities: ["Story Bible", "Chapter outlines", "Beat sheets", "Version history"],
  },
  {
    id: "character-forge",
    label: "Character Forge",
    path: "/character",
    icon: Users,
    tagline: "Cast & personas",
    description: "Design the Character Bible — profiles, relationships, arcs and voice consistency.",
    category: "llm",
    accent: "#A855F7",
    tabs: [
      { id: "roster", label: "Roster" },
      { id: "relationships", label: "Relationships" },
      { id: "arcs", label: "Arcs" },
    ],
    capabilities: ["Character Bible", "Relationship graph", "Persona voices"],
  },
  {
    id: "world-forge",
    label: "World Forge",
    path: "/world",
    icon: Globe2,
    tagline: "Lore & universe",
    description: "Craft the World Bible — locations, factions, timelines and the rules of reality.",
    category: "llm",
    accent: "#6366F1",
    tabs: [
      { id: "atlas", label: "Atlas" },
      { id: "factions", label: "Factions" },
      { id: "timeline", label: "Timeline" },
      { id: "rules", label: "Rules" },
    ],
    capabilities: ["World Bible", "Locations atlas", "Timeline", "Lore graph"],
  },
  {
    id: "image-forge",
    label: "Image Forge",
    path: "/image",
    icon: Image,
    tagline: "Visual generation",
    description: "Generate and manage concept art, key visuals and style references.",
    category: "image",
    accent: "#EC4899",
    tabs: [
      { id: "canvas", label: "Canvas" },
      { id: "gallery", label: "Gallery" },
      { id: "styles", label: "Styles" },
    ],
    capabilities: ["Concept art", "Style presets", "Reference boards"],
  },
  {
    id: "video-forge",
    label: "Video Forge",
    path: "/video",
    icon: Clapperboard,
    tagline: "Motion & scenes",
    description: "Compose shots, scenes and sequences on a professional timeline.",
    category: "video",
    accent: "#F43F5E",
    tabs: [
      { id: "timeline", label: "Timeline" },
      { id: "shots", label: "Shots" },
      { id: "renders", label: "Renders" },
    ],
    capabilities: ["Shot list", "Scene timeline", "Render queue"],
  },
  {
    id: "voice-forge",
    label: "Voice Forge",
    path: "/voice",
    icon: Mic,
    tagline: "Speech & dialogue",
    description: "Cast voices, generate dialogue and manage narration takes.",
    category: "voice",
    accent: "#F97316",
    tabs: [
      { id: "voices", label: "Voices" },
      { id: "lines", label: "Lines" },
      { id: "takes", label: "Takes" },
    ],
    capabilities: ["Voice casting", "Dialogue synthesis", "Take management"],
  },
  {
    id: "music-forge",
    label: "Music Forge",
    path: "/music",
    icon: Music,
    tagline: "Score & sound",
    description: "Compose scores, themes and adaptive soundtracks for your world.",
    category: "music",
    accent: "#EAB308",
    tabs: [
      { id: "tracks", label: "Tracks" },
      { id: "themes", label: "Themes" },
      { id: "library", label: "Library" },
    ],
    capabilities: ["Original score", "Leitmotifs", "Sound library"],
  },
  {
    id: "language-forge",
    label: "Language Forge",
    path: "/language",
    icon: Languages,
    tagline: "Translation & localization",
    description: "Localize every asset across languages with glossaries and tone control.",
    category: "translation",
    accent: "#14B8A6",
    tabs: [
      { id: "locales", label: "Locales" },
      { id: "glossary", label: "Glossary" },
      { id: "review", label: "Review" },
    ],
    capabilities: ["Multi-locale", "Glossaries", "Tone control"],
  },
  {
    id: "workflow-forge",
    label: "Workflow Forge",
    path: "/workflow",
    icon: Workflow,
    tagline: "Automation & pipelines",
    description: "Chain Forges into repeatable pipelines and creative automations.",
    accent: "#22C55E",
    tabs: [
      { id: "flows", label: "Flows" },
      { id: "runs", label: "Runs" },
      { id: "templates", label: "Templates" },
    ],
    capabilities: ["Node pipelines", "Scheduled runs", "Templates"],
  },
  {
    id: "publish-forge",
    label: "Publish Forge",
    path: "/publish",
    icon: Send,
    tagline: "Distribution",
    description: "Package and publish finished work to platforms and channels.",
    category: "publishing",
    accent: "#0EA5E9",
    tabs: [
      { id: "channels", label: "Channels" },
      { id: "releases", label: "Releases" },
      { id: "schedule", label: "Schedule" },
    ],
    capabilities: ["Multi-platform", "Release manager", "Scheduling"],
  },
  {
    id: "plugin-forge",
    label: "Plugin Forge",
    path: "/plugins",
    icon: Blocks,
    tagline: "Extend Akasha",
    description: "Install providers and extensions — grow the platform without touching core.",
    accent: "#94A3B8",
    tabs: [
      { id: "installed", label: "Installed" },
      { id: "marketplace", label: "Marketplace" },
      { id: "develop", label: "Develop" },
    ],
    capabilities: ["Provider plugins", "Sandboxed extensions", "Developer SDK"],
  },
];

export const getModule = (id: string): ModuleDef =>
  MODULES.find((m) => m.id === id) as ModuleDef;

export interface NavItem {
  moduleId?: string;
  label: string;
  path: string;
  icon: LucideIcon;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

const m = (id: string): NavItem => {
  const mod = getModule(id);
  return { moduleId: id, label: mod.label, path: mod.path, icon: mod.icon };
};

export const NAV_SECTIONS: NavSection[] = [
  { title: "Overview", items: [m("akasha-core"), m("akasha-brain")] },
  {
    title: "Create",
    items: [
      m("story-forge"),
      m("character-forge"),
      m("world-forge"),
      m("image-forge"),
      m("video-forge"),
      m("voice-forge"),
      m("music-forge"),
      m("workflow-forge"),
      m("publish-forge"),
    ],
  },
  {
    title: "Library",
    items: [
      { label: "Assets", path: "/assets", icon: Boxes },
      { label: "Projects", path: "/projects", icon: FolderOpen },
      m("plugin-forge"),
    ],
  },
  {
    title: "System",
    items: [{ label: "Settings", path: "/settings", icon: Settings }],
  },
];
