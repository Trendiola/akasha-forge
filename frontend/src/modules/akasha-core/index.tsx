import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity, ArrowUpRight, BrainCircuit, CheckCircle2, CircleOff, Clock3, Cpu,
  FolderKanban, Image as ImageIcon, Plus, Radio, Sparkles, Users, Workflow,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { MODULES } from "@/config/modules";
import { useProjects } from "@/features/projects/hooks";
import { useProviders } from "@/features/providers/hooks";
import { useForgeItems } from "@/features/forge/hooks";
import { useActiveProject } from "@/features/projects/useActiveProject";
import { useApp } from "@/store/app-context";
import { api } from "@/lib/api";
import { CreateProjectDialog } from "@/features/projects/CreateProjectDialog";
import { cn } from "@/lib/utils";

const FORGES = MODULES.filter((module) => module.id !== "akasha-core" && module.id !== "plugin-forge");

function relativeTime(value?: string) {
  if (!value) return "Just now";
  const seconds = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AkashaCore() {
  const { data: projects = [], isLoading: projectsLoading } = useProjects();
  const { data: providers = [], isLoading: providersLoading } = useProviders();
  const activeProject = useActiveProject();
  const { data: imageAssets = [] } = useForgeItems(activeProject?.id, "image", "asset");
  const { setActiveProjectId } = useApp();
  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const health = useQuery({
    queryKey: ["system-health"],
    queryFn: async () => (await api.get("/health")).data as { status: string; version: string },
    retry: 1,
    refetchInterval: 30_000,
  });

  const enabledProviders = providers.filter((provider) => provider.enabled && provider.configured);
  const readyProviders = enabledProviders.filter((provider) => provider.status === "ready");
  const readiness = providers.length ? Math.round((readyProviders.length / providers.length) * 100) : 0;
  const primaryProvider = readyProviders.find((provider) => provider.is_default) ?? readyProviders[0];

  return (
    <div className="core-dashboard pb-8">
      <section className="core-hero">
        <div className="core-hero-grid" aria-hidden="true" />
        <div className="core-hero-copy">
          <p className="core-eyebrow"><Sparkles className="h-3.5 w-3.5" /> Welcome to Akasha Forge</p>
          <h1 className="core-brand-title"><span>AKASHA</span><span>FORGE</span></h1>
          <p className="core-os-label">The Creative Operating System</p>
          <p className="core-manifesto">Think. Create. Manifest.</p>
          <p className="core-description">A unified creative intelligence environment for shaping stories, worlds, characters, imagery, motion and sound.</p>
          <div className="core-actions">
            <Button asChild className="h-10 gap-2 rounded-lg bg-primary px-5 font-semibold shadow-[0_10px_32px_rgba(109,59,255,.25)] hover:bg-primary/90">
              <Link to="/brain"><BrainCircuit className="h-4 w-4" /> Open Akasha Brain</Link>
            </Button>
            <Button variant="outline" className="h-10 gap-2 rounded-lg border-white/10 bg-white/[.025] px-5 hover:bg-white/[.06]" onClick={() => setProjectDialogOpen(true)} data-testid="core-new-project">
              <Plus className="h-4 w-4" /> New Project
            </Button>
          </div>
        </div>

        <div className="intelligence-core" aria-label="AKASHA intelligence core">
          <div className="core-illumination" />
          <div className="precision-orbit orbit-alpha" /><div className="precision-orbit orbit-beta" /><div className="precision-orbit orbit-gamma" />
          <div className="core-axis core-axis-horizontal" /><div className="core-axis core-axis-vertical" />
          <span className="energy-node energy-node-a" /><span className="energy-node energy-node-b" /><span className="energy-node energy-node-c" /><span className="energy-node energy-node-d" />
          <div className="core-emblem-halo"><img src="/branding/akasha-emblem-transparent.png" alt="Official AKASHA emblem" className="core-emblem" /></div>
        </div>
      </section>

      <section className="telemetry-strip" aria-label="System telemetry">
        <Telemetry icon={Cpu} label="AI Providers" value={providersLoading ? "Checking" : `${readyProviders.length} ready`} detail={`${enabledProviders.length} configured / ${providers.length} available`} state={readyProviders.length ? "online" : "offline"} />
        <Telemetry icon={FolderKanban} label="Active Project" value={activeProject?.name ?? "None"} detail={activeProject ? `${activeProject.type} workspace` : "No workspace selected"} state={activeProject ? "online" : "neutral"} />
        <Telemetry icon={Radio} label="System Status" value={health.isSuccess ? "Operational" : health.isError ? "Offline" : "Checking"} detail={health.data?.version ? `Local engine v${health.data.version}` : "Backend connection"} state={health.isSuccess ? "online" : health.isError ? "offline" : "neutral"} />
        <Telemetry icon={ImageIcon} label="Project Assets" value={activeProject ? String(imageAssets.length) : "—"} detail={activeProject ? "Visible in active project" : "Select a project"} state="neutral" />
      </section>

      <section className="home-section forge-suite">
        <SectionHeading eyebrow="Creative workspaces" title="Forge Modules" meta={`${FORGES.length} modules`} />
        <div className="forge-grid">
          {FORGES.map((module, index) => {
            const Icon = module.icon;
            return (
              <motion.div key={module.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * .018 }}>
                <Link to={module.path} className="forge-module-card group" data-testid={`quick-${module.id}`} style={{ "--module-accent": module.accent } as React.CSSProperties}>
                  <span className="forge-module-icon"><Icon className="h-[18px] w-[18px]" /></span>
                  <span className="min-w-0 flex-1"><strong>{module.label}</strong><small>{module.tagline}</small></span>
                  <span className="forge-open">Open <ArrowUpRight className="h-3 w-3" /></span>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </section>

      <section className="home-workspace-grid">
        <div className="ai-system-panel">
          <div className="panel-heading"><div><p>Intelligence layer</p><h2>AI System Status</h2></div><span className={cn("system-indicator", readyProviders.length && "is-online")} /></div>
          <div className="ai-readiness">
            <div><strong>{readiness}%</strong><span>Ready</span></div>
            <div className="readiness-track"><span style={{ width: `${readiness}%` }} /></div>
          </div>
          <dl className="ai-details">
            <div><dt>Providers</dt><dd>{readyProviders.length} / {providers.length}</dd></div>
            <div><dt>Primary Model</dt><dd>{primaryProvider?.default_model || "Not configured"}</dd></div>
            <div><dt>Connection</dt><dd className={readyProviders.length ? "text-emerald-300" : "text-white/45"}>{readyProviders.length ? "Online" : "Offline"}</dd></div>
          </dl>
          <Button asChild variant="outline" size="sm" className="mt-4 w-full gap-2 rounded-lg border-primary/25 bg-primary/[.05] text-violet-200 hover:bg-primary/[.1]">
            <Link to="/providers"><Cpu className="h-3.5 w-3.5" /> Connect AI Providers</Link>
          </Button>
        </div>

        <div className="dashboard-panel">
          <SectionHeading eyebrow="Direct access" title="Quick Actions" />
          <div className="quick-actions-grid">
            <QuickAction icon={Plus} label="New Project" onClick={() => setProjectDialogOpen(true)} />
            <QuickAction icon={BrainCircuit} label="Akasha Brain" to="/brain" />
            <QuickAction icon={Sparkles} label="Create Story" to="/story" />
            <QuickAction icon={Users} label="Create Character" to="/character" />
            <QuickAction icon={ImageIcon} label="Open Image Forge" to="/image" />
            <QuickAction icon={Workflow} label="Workflow Forge" to="/workflow" />
          </div>
        </div>

        <div className="dashboard-panel activity-panel">
          <SectionHeading eyebrow="Workspace pulse" title="Recent Activity" meta={<Activity className="h-4 w-4" />} />
          {projects.length ? (
            <div className="activity-list">{projects.slice(0, 4).map((project) => (
              <div key={project.id} className="activity-row"><span className="activity-mark" style={{ background: project.color }} /><span className="min-w-0 flex-1"><strong>{project.name}</strong><small>Project workspace updated</small></span><time>{relativeTime(project.updated_at)}</time></div>
            ))}</div>
          ) : <CompactEmpty icon={Clock3} title="No activity yet" detail="Real project and Forge activity will appear here." />}
        </div>
      </section>

      <section className="home-section">
        <SectionHeading eyebrow="Continue creating" title="Recent Projects" meta={projects.length ? <Link to="/projects">View all</Link> : undefined} />
        {projectsLoading ? <div className="project-loading" /> : projects.length ? (
          <div className="recent-project-grid">{projects.slice(0, 6).map((project) => (
            <Link key={project.id} to="/projects" onClick={() => setActiveProjectId(project.id)} className={cn("project-preview", activeProject?.id === project.id && "is-active")} data-testid={`recent-project-${project.id}`}>
              <span className="project-accent" style={{ background: project.color }} /><span className="min-w-0 flex-1"><strong>{project.name}</strong><small>{project.description || "No description yet."}</small></span>
              {activeProject?.id === project.id ? <CheckCircle2 className="h-4 w-4 text-violet-300" /> : <span className="project-time">{relativeTime(project.updated_at)}</span>}
            </Link>
          ))}</div>
        ) : (
          <div className="project-empty"><div className="project-empty-icon"><CircleOff className="h-5 w-5" /></div><div><h3>Your creative universe starts here</h3><p>Create your first project to connect stories, characters, worlds, assets and workflows.</p></div><Button onClick={() => setProjectDialogOpen(true)} className="ml-auto shrink-0 gap-2"><Plus className="h-4 w-4" /> Create New Project</Button></div>
        )}
      </section>

      <CreateProjectDialog open={projectDialogOpen} onOpenChange={setProjectDialogOpen} />
    </div>
  );
}

function SectionHeading({ eyebrow, title, meta }: { eyebrow: string; title: string; meta?: React.ReactNode }) {
  return <div className="section-heading"><div><p>{eyebrow}</p><h2>{title}</h2></div>{meta && <span className="section-meta">{meta}</span>}</div>;
}

function Telemetry({ icon: Icon, label, value, detail, state }: { icon: any; label: string; value: string; detail: string; state: "online" | "offline" | "neutral" }) {
  return <div className="telemetry-item"><span className={cn("telemetry-icon", state)}><Icon className="h-4 w-4" /></span><span className="min-w-0"><small>{label}</small><strong>{value}</strong><em>{detail}</em></span></div>;
}

function QuickAction({ icon: Icon, label, to, onClick }: { icon: any; label: string; to?: string; onClick?: () => void }) {
  const content = <><span><Icon className="h-4 w-4" /></span><strong>{label}</strong><ArrowUpRight className="ml-auto h-3.5 w-3.5" /></>;
  return to ? <Link to={to} className="quick-action">{content}</Link> : <button onClick={onClick} className="quick-action text-left">{content}</button>;
}

function CompactEmpty({ icon: Icon, title, detail }: { icon: any; title: string; detail: string }) {
  return <div className="compact-empty"><Icon className="h-5 w-5" /><div><strong>{title}</strong><p>{detail}</p></div></div>;
}
