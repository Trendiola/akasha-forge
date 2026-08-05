import React from "react";
import { Link } from "react-router-dom";
import { Plus, Sparkles, FolderOpen, CircleDashed } from "lucide-react";
import type { ModuleDef } from "@/config/modules";
import { PageHeader } from "./PageHeader";
import { EmptyState } from "./EmptyState";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useApp } from "@/store/app-context";
import { useProjects } from "@/features/projects/hooks";

interface ModuleShellProps {
  module: ModuleDef;
  content?: Record<string, React.ReactNode>;
  requireProject?: boolean;
}

export function ModuleShell({ module, content, requireProject = true }: ModuleShellProps) {
  const { activeProjectId } = useApp();
  const { data: projects = [] } = useProjects();
  const activeProject = projects.find((p) => p.id === activeProjectId);

  return (
    <div className="animate-in fade-in duration-500" data-testid={`module-${module.id}`}>
      <PageHeader
        icon={module.icon}
        title={module.label}
        tagline={module.tagline}
        description={module.description}
        accent={module.accent}
        actions={
          <Button
            data-testid={`${module.id}-new-btn`}
            className="gap-2 font-heading font-semibold"
            style={{ background: module.accent }}
          >
            <Plus className="h-4 w-4" /> New
          </Button>
        }
      />

      {/* Capability strip */}
      <div className="mb-6 flex flex-wrap gap-2">
        {module.capabilities.map((cap) => (
          <Badge
            key={cap}
            variant="outline"
            className="rounded-full border-border bg-secondary/40 px-3 py-1 text-xs font-normal text-muted-foreground"
          >
            <Sparkles className="mr-1.5 h-3 w-3" style={{ color: module.accent }} />
            {cap}
          </Badge>
        ))}
      </div>

      {/* Project context banner */}
      {requireProject && !activeProject && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-border bg-card/50 px-4 py-3 text-sm">
          <CircleDashed className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">
            No active project selected. {module.label} works within a project context.
          </span>
          <Link to="/projects" className="ml-auto">
            <Button size="sm" variant="outline" className="gap-1.5">
              <FolderOpen className="h-3.5 w-3.5" /> Open Projects
            </Button>
          </Link>
        </div>
      )}

      <Tabs defaultValue={module.tabs[0]?.id} className="w-full">
        <TabsList className="mb-6 h-auto flex-wrap justify-start gap-1 bg-secondary/40 p-1">
          {module.tabs.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              data-testid={`${module.id}-tab-${tab.id}`}
              className="rounded-md px-4 py-1.5 text-sm data-[state=active]:bg-background data-[state=active]:shadow-sm"
            >
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {module.tabs.map((tab) => (
          <TabsContent key={tab.id} value={tab.id} className="mt-0">
            {content && content[tab.id] !== undefined ? (
              content[tab.id]
            ) : (
              <EmptyState
                icon={module.icon}
                accent={module.accent}
                title={`${tab.label} is ready to build`}
                description={
                  activeProject
                    ? `Start creating ${tab.label.toLowerCase()} for “${activeProject.name}”. This workspace is scaffolded and ready for AI generation once providers are connected.`
                    : `This ${tab.label.toLowerCase()} workspace is fully scaffolded. Select a project to begin.`
                }
                action={
                  <Button
                    variant="outline"
                    className="gap-2"
                    data-testid={`${module.id}-${tab.id}-create`}
                  >
                    <Plus className="h-4 w-4" /> Create {tab.label}
                  </Button>
                }
              />
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
