import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Activity, ArrowRight, BrainCircuit, CheckCircle2, Clock3, CloudOff, Cpu, FolderKanban, Image as ImageIcon, Layers3, Plus, Radio, Sparkles } from "lucide-react";
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

const FORGES = MODULES.filter((module) => !["akasha-core", "akasha-brain", "plugin-forge"].includes(module.id));

function formatRelative(value?: string) {
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
  const [dialogOpen, setDialogOpen] = useState(false);
  const health = useQuery({ queryKey: ["system-health"], queryFn: async () => (await api.get("/health")).data as { status: string; version: string }, retry: 1, refetchInterval: 30_000 });
  const readyProviders = providers.filter((provider) => provider.enabled && provider.configured && provider.status === "ready");
  const configuredProviders = providers.filter((provider) => provider.enabled && provider.configured);

  return (
    <div className="core-dashboard space-y-7 pb-8">
      <section className="core-hero grain relative min-h-[410px] overflow-hidden rounded-[28px] border border-white/[0.08] px-7 py-8 sm:px-10 lg:px-12">
        <div className="core-stars" aria-hidden="true" /><div className="core-orbit core-orbit-one" aria-hidden="true" /><div className="core-orbit core-orbit-two" aria-hidden="true" />
        <div className="relative z-10 grid min-h-[345px] items-center gap-8 lg:grid-cols-[1.08fr_.92fr]">
          <div className="max-w-2xl">
            <div className="mb-6 flex items-center gap-3">
              <img src="/branding/akasha-forge-official.png" alt="AKASHA FORGE" className="h-12 w-12 rounded-xl object-contain shadow-[0_0_35px_rgba(109,59,255,.35)]" />
              <div><p className="text-[11px] font-bold uppercase tracking-[.27em] text-violet-200/75">AKASHA FORGE</p><p className="mt-1 text-[10px] uppercase tracking-[.2em] text-cyan-200/45">The Creative Operating System</p></div>
            </div>
            <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[.24em] text-violet-300"><Sparkles className="h-3.5 w-3.5" /> Creative command center</p>
            <h1 className="max-w-xl text-4xl font-semibold leading-[1.03] text-white sm:text-5xl xl:text-[58px]">Think. Create. <span className="text-akasha-gradient">Manifest.</span></h1>
            <p className="mt-5 max-w-xl text-sm leading-6 text-white/52 sm:text-[15px]">One focused environment for stories, worlds, imagery, motion, sound and intelligent production.</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button asChild size="lg" className="h-11 gap-2 rounded-xl bg-primary px-5 shadow-[0_12px_40px_rgba(109,59,255,.3)] hover:bg-primary/90"><Link to="/brain"><BrainCircuit className="h-4 w-4" /> Open Akasha Brain</Link></Button>
              <Button size="lg" variant="outline" className="h-11 gap-2 rounded-xl border-white/10 bg-white/[.035] px-5 hover:bg-white/[.07]" onClick={() => setDialogOpen(true)} data-testid="core-new-project"><Plus className="h-4 w-4" /> New Project</Button>
            </div>
          </div>
          <div className="relative mx-auto flex h-[280px] w-full max-w-[390px] items-center justify-center" aria-hidden="true">
            <div className="core-cosmic-glow" /><div className="core-sigil-ring core-sigil-ring-outer" /><div className="core-sigil-ring core-sigil-ring-inner" />
            <div className="relative z-10 flex h-36 w-36 items-center justify-center rounded-full border border-violet-300/20 bg-black/30 shadow-[0_0_70px_rgba(109,59,255,.28)] backdrop-blur-xl"><img src="/branding/akasha-forge-official.png" alt="" className="h-28 w-28 object-contain" /></div>
            <span className="core-orbit-node node-one" /><span className="core-orbit-node node-two" /><span className="core-orbit-node node-three" />
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard icon={Cpu} label="AI providers" value={providersLoading ? "Checking" : readyProviders.length ? `${readyProviders.length} ready` : configuredProviders.length ? `${configuredProviders.length} configured` : "Unconfigured"} detail={readyProviders.length ? "Validated engines available" : "No validated AI engine"} tone={readyProviders.length ? "ready" : "offline"} />
        <StatusCard icon={FolderKanban} label="Active project" value={activeProject?.name ?? "No project"} detail={activeProject ? `${activeProject.type} workspace` : "Create or select a workspace"} tone={activeProject ? "ready" : "neutral"} />
        <StatusCard icon={Radio} label="System" value={health.isSuccess ? "Operational" : health.isError ? "Offline" : "Checking"} detail={health.data?.version ? `Engine v${health.data.version}` : "Local backend connection"} tone={health.isSuccess ? "ready" : health.isError ? "offline" : "neutral"} />
        <StatusCard icon={ImageIcon} label="Project assets" value={activeProject ? String(imageAssets.length) : "—"} detail={activeProject ? "Images in active workspace" : "Select a project to inspect"} tone="neutral" />
      </section>

      <section><SectionTitle eyebrow="Creative suite" title="Forge Modules" action={<span className="text-xs text-white/32">{FORGES.length} connected workspaces</span>} />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{FORGES.map((module, index) => { const Icon = module.icon; return (
          <motion.div key={module.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * .025 }}><Link to={module.path} className="forge-module-card group flex min-h-[132px] items-start gap-4 rounded-2xl p-4" data-testid={`quick-${module.id}`}>
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border" style={{ color: module.accent, borderColor: `${module.accent}30`, background: `${module.accent}12` }}><Icon className="h-5 w-5" /></div>
            <div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><h3 className="font-heading text-sm font-semibold text-white/90">{module.label}</h3><ArrowRight className="h-3.5 w-3.5 text-white/20 transition-transform group-hover:translate-x-1 group-hover:text-white/60" /></div><p className="mt-1 text-[11px] font-medium uppercase tracking-[.12em]" style={{ color: module.accent }}>{module.tagline}</p><p className="mt-2 line-clamp-2 text-xs leading-5 text-white/38">{module.description}</p></div>
          </Link></motion.div>); })}</div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[.82fr_1.18fr]">
        <div className="akasha-panel rounded-2xl p-5"><SectionTitle eyebrow="Shortcuts" title="Quick Actions" /><div className="grid grid-cols-2 gap-3"><QuickAction to="/brain" icon={BrainCircuit} label="Ask Akasha" detail="Open intelligence" /><QuickAction to="/image" icon={ImageIcon} label="Create image" detail="Open canvas" /><QuickAction to="/story" icon={Layers3} label="Build story" detail="Open bible" /><button onClick={() => setDialogOpen(true)} className="quick-action text-left"><span className="quick-action-icon"><Plus className="h-4 w-4" /></span><span><strong>New project</strong><small>Start a workspace</small></span></button></div></div>
        <div className="akasha-panel rounded-2xl p-5"><SectionTitle eyebrow="Workspace pulse" title="Recent Activity" action={<Activity className="h-4 w-4 text-white/25" />} />
          {projects.length === 0 ? <DashboardEmpty icon={Clock3} title="No activity yet" detail="Project changes and creative output will appear here." /> : <div className="space-y-2">{projects.slice(0, 4).map((project) => <div key={project.id} className="flex items-center gap-3 rounded-xl border border-white/[.05] bg-white/[.018] px-3.5 py-3"><span className="h-8 w-1 rounded-full" style={{ background: project.color }} /><div className="min-w-0 flex-1"><p className="truncate text-sm text-white/78">{project.name}</p><p className="mt-0.5 text-xs text-white/34">Workspace updated</p></div><span className="text-[11px] text-white/28">{formatRelative(project.updated_at)}</span></div>)}</div>}
        </div>
      </section>

      <section><SectionTitle eyebrow="Continue creating" title="Recent Projects" action={<Link to="/projects" className="text-xs text-violet-300/75 hover:text-violet-200">View all</Link>} />
        {projectsLoading ? <div className="h-36 animate-pulse rounded-2xl border border-white/[.06] bg-white/[.02]" /> : projects.length === 0 ? <DashboardEmpty icon={FolderKanban} title="Your first universe begins here" detail="Create a project to connect every Forge to the same creative context." action={<Button onClick={() => setDialogOpen(true)} size="sm" className="gap-2"><Plus className="h-3.5 w-3.5" /> Create project</Button>} /> : <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{projects.slice(0, 6).map((project) => <Link key={project.id} to="/projects" onClick={() => setActiveProjectId(project.id)} className={cn("project-preview group relative overflow-hidden rounded-2xl border p-4", activeProject?.id === project.id ? "border-primary/35" : "border-white/[.065]")} data-testid={`recent-project-${project.id}`}><div className="absolute inset-y-0 left-0 w-[3px]" style={{ background: project.color }} /><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="truncate font-heading text-sm font-semibold">{project.name}</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-white/38">{project.description || "No description yet."}</p></div>{activeProject?.id === project.id && <CheckCircle2 className="h-4 w-4 shrink-0 text-violet-300" />}</div><div className="mt-4 flex items-center justify-between text-[10px] uppercase tracking-[.1em] text-white/28"><span>{project.type}</span><span>{formatRelative(project.updated_at)}</span></div></Link>)}</div>}
      </section>
      <CreateProjectDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  );
}

function SectionTitle({ eyebrow, title, action }: { eyebrow: string; title: string; action?: React.ReactNode }) { return <div className="mb-4 flex items-end justify-between gap-4"><div><p className="text-[9px] font-bold uppercase tracking-[.2em] text-violet-300/55">{eyebrow}</p><h2 className="mt-1 text-lg font-semibold text-white/90">{title}</h2></div>{action}</div>; }
function StatusCard({ icon: Icon, label, value, detail, tone }: { icon: any; label: string; value: string; detail: string; tone: "ready" | "offline" | "neutral" }) { return <div className="status-card flex items-center gap-3 rounded-2xl p-4"><span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", tone === "ready" ? "bg-emerald-400/[.08] text-emerald-300" : tone === "offline" ? "bg-amber-400/[.08] text-amber-300" : "bg-violet-400/[.08] text-violet-300")}>{tone === "offline" ? <CloudOff className="h-4 w-4" /> : <Icon className="h-4 w-4" />}</span><div className="min-w-0"><p className="text-[10px] uppercase tracking-[.12em] text-white/30">{label}</p><p className="mt-0.5 truncate text-sm font-semibold text-white/82">{value}</p><p className="mt-0.5 truncate text-[11px] text-white/28">{detail}</p></div></div>; }
function QuickAction({ to, icon: Icon, label, detail }: { to: string; icon: any; label: string; detail: string }) { return <Link to={to} className="quick-action"><span className="quick-action-icon"><Icon className="h-4 w-4" /></span><span><strong>{label}</strong><small>{detail}</small></span></Link>; }
function DashboardEmpty({ icon: Icon, title, detail, action }: { icon: any; title: string; detail: string; action?: React.ReactNode }) { return <div className="flex min-h-[138px] flex-col items-center justify-center rounded-2xl border border-dashed border-white/[.075] bg-white/[.012] px-5 text-center"><Icon className="mb-3 h-5 w-5 text-white/20" /><p className="text-sm font-medium text-white/65">{title}</p><p className="mt-1 max-w-md text-xs leading-5 text-white/30">{detail}</p>{action && <div className="mt-4">{action}</div>}</div>; }
