import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FolderKanban, Boxes, Cpu, Layers, Plus, ArrowRight, Clock } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { MODULES } from "@/config/modules";
import { useProjects } from "@/features/projects/hooks";
import { useProviders } from "@/features/providers/hooks";
import { useApp } from "@/store/app-context";
import { CreateProjectDialog } from "@/features/projects/CreateProjectDialog";

const CREATE_MODULES = MODULES.filter((m) =>
  ["story-forge", "character-forge", "world-forge", "image-forge", "video-forge", "music-forge"].includes(m.id)
);

export default function AkashaCore() {
  const { data: projects = [] } = useProjects();
  const { data: providers = [] } = useProviders();
  const { setActiveProjectId } = useApp();
  const [dialogOpen, setDialogOpen] = useState(false);
  const enabledProviders = providers.filter((p) => p.enabled).length;

  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader
        title="Welcome to Akasha Forge"
        tagline="Akasha Core"
        description="The Creative Operating System. Orchestrate every Forge from a single command center."
        actions={
          <Button
            className="gap-2 font-heading font-semibold"
            onClick={() => setDialogOpen(true)}
            data-testid="core-new-project"
          >
            <Plus className="h-4 w-4" /> New project
          </Button>
        }
      />

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={FolderKanban} label="Projects" value={projects.length} hint="Total workspaces" accent="#6D3BFF" />
        <StatCard icon={Layers} label="Modules" value={MODULES.length} hint="Creative Forges" accent="#A855F7" />
        <StatCard icon={Cpu} label="Providers" value={`${enabledProviders}/${providers.length}`} hint="Enabled engines" accent="#0EA5E9" />
        <StatCard icon={Boxes} label="Assets" value={0} hint="Generated so far" accent="#14B8A6" />
      </div>

      {/* Quick create */}
      <section className="mb-10">
        <h2 className="mb-4 font-display text-lg font-semibold tracking-tight">Create something</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {CREATE_MODULES.map((mod, i) => {
            const Icon = mod.icon;
            return (
              <motion.div
                key={mod.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <Link
                  to={mod.path}
                  data-testid={`quick-${mod.id}`}
                  className="group flex flex-col gap-3 rounded-2xl border border-border bg-card/60 p-4 transition-all hover:-translate-y-1 hover:border-primary/40"
                >
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-xl transition-transform group-hover:scale-110"
                    style={{ background: `${mod.accent}18` }}
                  >
                    <Icon className="h-5 w-5" style={{ color: mod.accent }} />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{mod.label}</p>
                    <p className="text-xs text-muted-foreground">{mod.tagline}</p>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Recent projects */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold tracking-tight">Recent projects</h2>
          <Link to="/projects" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>
        {projects.length === 0 ? (
          <EmptyState
            icon={FolderKanban}
            title="No projects yet"
            description="Create your first project to unlock the Story, Character and World bibles and start forging."
            action={
              <Button className="gap-2" onClick={() => setDialogOpen(true)} data-testid="empty-new-project">
                <Plus className="h-4 w-4" /> Create project
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.slice(0, 6).map((p) => (
              <Link
                key={p.id}
                to="/projects"
                onClick={() => setActiveProjectId(p.id)}
                data-testid={`recent-project-${p.id}`}
                className="group relative overflow-hidden rounded-2xl border border-border bg-card/60 p-5 transition-all hover:-translate-y-1 hover:border-primary/40"
              >
                <div className="absolute inset-x-0 top-0 h-1" style={{ background: p.color }} />
                <div className="flex items-start justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ background: `${p.color}22` }}>
                    <span className="font-display text-lg font-bold" style={{ color: p.color }}>
                      {p.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </div>
                <p className="mt-4 truncate font-heading text-base font-semibold">{p.name}</p>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                  {p.description || "No description yet."}
                </p>
                <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span className="capitalize">{p.type}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <CreateProjectDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  );
}
