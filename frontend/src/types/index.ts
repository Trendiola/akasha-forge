// Shared domain types for Akasha Forge

export type ProviderCategory =
  | "llm"
  | "image"
  | "video"
  | "voice"
  | "music"
  | "translation"
  | "publishing";

export interface Project {
  id: string;
  name: string;
  description: string;
  type: string;
  status: "active" | "archived" | "draft";
  color: string;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Provider {
  id: string;
  name: string;
  category: ProviderCategory;
  kind: "api" | "local" | "plugin";
  base_url: string;
  enabled: boolean;
  is_default: boolean;
  models: string[];
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AppSettings {
  id: string;
  general: Record<string, any>;
  appearance: Record<string, any>;
  language: Record<string, any>;
  publishing: Record<string, any>;
  storage: Record<string, any>;
  shortcuts: Record<string, any>;
  updated_at: string;
}
