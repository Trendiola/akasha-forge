import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Sparkles, Clapperboard, Film, ListVideo, PlayCircle, RotateCcw,
  Download, CheckCircle2, XCircle, Loader2, Captions, ChevronDown, ChevronRight,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { fileUrl } from "@/lib/api";
import { useActiveProject } from "@/features/projects/useActiveProject";
import {
  usePlanVideo, useGenerateJobs, useProductionStatus, useProductionNodes,
  useVideoJobs, useRetryJob, useProduceRunner, type ProductionNode, type RenderJob,
} from "@/features/video/hooks";

const ACCENT = "#F43F5E";

const errMsg = (e: any, fallback: string) => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (d?.message) return d.message;
  return fallback;
};

function StatChip({ label, value, testid, tone = "muted" }: { label: string; value: number; testid: string; tone?: string }) {
  const tones: Record<string, string> = {
    muted: "border-border bg-card/60 text-muted-foreground",
    active: "border-sky-400/40 bg-sky-400/10 text-sky-200",
    done: "border-emerald-400/40 bg-emerald-400/10 text-emerald-200",
    fail: "border-rose-400/40 bg-rose-400/10 text-rose-200",
  };
  return (
    <div className={`flex min-w-[92px] flex-col rounded-lg border px-3 py-2 ${tones[tone]}`} data-testid={testid}>
      <span className="text-xs uppercase tracking-wide opacity-80">{label}</span>
      <span className="font-heading text-2xl font-semibold">{value}</span>
    </div>
  );
}

const JOB_TONE: Record<string, { label: string; cls: string }> = {
  draft: { label: "Draft", cls: "border-border text-muted-foreground" },
  queued: { label: "Queued", cls: "border-amber-400/40 text-amber-200 bg-amber-400/10" },
  submitting: { label: "Submitting", cls: "border-sky-400/40 text-sky-200 bg-sky-400/10" },
  processing: { label: "Processing", cls: "border-sky-400/40 text-sky-200 bg-sky-400/10" },
  completed: { label: "Completed", cls: "border-emerald-400/40 text-emerald-200 bg-emerald-400/10" },
  failed: { label: "Failed", cls: "border-rose-400/40 text-rose-200 bg-rose-400/10" },
  cancelled: { label: "Cancelled", cls: "border-border text-muted-foreground" },
};

export function MovieStudio() {
  const project = useActiveProject();
  const projectId = project?.id;

  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(30);
  const [clip, setClip] = useState(8);
  const [aspect, setAspect] = useState("16:9");
  const [style, setStyle] = useState("");
  const [showShots, setShowShots] = useState(false);

  const plan = usePlanVideo(projectId);
  const genJobs = useGenerateJobs(projectId);
  const retry = useRetryJob(projectId);
  const runner = useProduceRunner(projectId);

  const { data: statusData } = useProductionStatus(projectId);
  const { data: nodes = [] } = useProductionNodes(projectId);
  const { data: jobs = [] } = useVideoJobs(projectId);

  // Live status: the produce runner's fresh view wins while it is driving.
  const status = runner.status ?? statusData ?? null;

  const shots = useMemo(() => nodes.filter((n: ProductionNode) => n.type === "shot").sort((a, b) => a.order - b.order), [nodes]);
  const scenes = useMemo(() => nodes.filter((n: ProductionNode) => n.type === "scene").sort((a, b) => a.order - b.order), [nodes]);
  const jobByShot = useMemo(() => {
    const m = new Map<string, RenderJob>();
    jobs.forEach((j) => { if (j.shot_id) m.set(j.shot_id, j); });
    return m;
  }, [jobs]);

  const hasPlan = shots.length > 0;
  const hasJobs = (status?.total_jobs ?? jobs.length) > 0;
  const finalAsset = status?.final_asset_id || "";
  const producing = runner.producing;
  const blocked = status?.status === "failed";

  const onPlan = async () => {
    if (!projectId) return;
    if (!prompt.trim()) { toast.error("Describe your video idea first."); return; }
    try {
      const res = await plan.mutateAsync({
        project_id: projectId, prompt: prompt.trim(),
        target_duration_seconds: Number(duration) || 30,
        clip_duration_seconds: Number(clip) || 8,
        aspect_ratio: aspect, style: style.trim() || undefined,
      });
      if (res.status === "planned") {
        toast.success(`Plan ready — ${res.estimated_total_clips} shots across ${res.scenes?.length ?? 0} scenes`);
      } else {
        toast.warning(res.warning || "Could not generate a plan.");
      }
    } catch (e) { toast.error(errMsg(e, "Planning failed. Please try again.")); }
  };

  const onGenerateJobs = async () => {
    if (!projectId) return;
    try {
      const res = await genJobs.mutateAsync({ project_id: projectId, aspect_ratio: aspect });
      toast.success(`${res.created + res.updated} render jobs ready`);
      if (res.warning) toast.warning(res.warning);
    } catch (e) { toast.error(errMsg(e, "Could not generate render jobs.")); }
  };

  const onProduce = async () => {
    if (!projectId) return;
    try { await runner.start(); }
    catch (e) { toast.error(errMsg(e, "Production could not be started.")); }
  };

  const onRetry = async (jobId: string) => {
    try { await retry.mutateAsync(jobId); toast.success("Shot re-queued. Click Produce to continue."); }
    catch (e) { toast.error(errMsg(e, "Retry failed.")); }
  };

  if (!project) return null;

  return (
    <div className="space-y-6" data-testid="movie-studio">
      {/* STEP 1 — Prompt */}
      <Card className="border-border/70 bg-card/60" data-testid="movie-studio-prompt">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-heading">
            <span className="grid h-8 w-8 place-items-center rounded-lg" style={{ background: `${ACCENT}22`, color: ACCENT }}><Sparkles className="h-4 w-4" /></span>
            One-Prompt Movie
          </CardTitle>
          <CardDescription>Describe your idea. Akasha Brain plans the scenes and shots, then renders and assembles a final MP4.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="ms-prompt">Video idea</Label>
            <Textarea id="ms-prompt" data-testid="movie-studio-idea" rows={3}
              placeholder="A cinematic short about a lone lighthouse keeper during a storm…"
              value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1.5">
              <Label htmlFor="ms-duration">Target duration (sec)</Label>
              <Input id="ms-duration" data-testid="movie-studio-duration" type="number" min={4}
                value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ms-clip">Clip length (sec)</Label>
              <Input id="ms-clip" data-testid="movie-studio-clip" type="number" min={2}
                value={clip} onChange={(e) => setClip(Number(e.target.value))} />
            </div>
            <div className="space-y-1.5">
              <Label>Aspect ratio</Label>
              <Select value={aspect} onValueChange={setAspect}>
                <SelectTrigger data-testid="movie-studio-aspect"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="16:9">16:9 — Landscape</SelectItem>
                  <SelectItem value="9:16">9:16 — Vertical</SelectItem>
                  <SelectItem value="1:1">1:1 — Square</SelectItem>
                  <SelectItem value="21:9">21:9 — Cinematic</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ms-style">Visual style</Label>
              <Input id="ms-style" data-testid="movie-studio-style" placeholder="cinematic, noir…"
                value={style} onChange={(e) => setStyle(e.target.value)} />
            </div>
          </div>
          <Button data-testid="movie-studio-plan-btn" onClick={onPlan} disabled={plan.isPending}
            className="gap-2" style={{ background: ACCENT }}>
            {plan.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {hasPlan ? "Re-plan" : "Generate Plan"}
          </Button>
        </CardContent>
      </Card>

      {/* STEP 2 — Plan review */}
      {hasPlan && (
        <Card className="border-border/70 bg-card/60" data-testid="movie-studio-plan">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-heading"><Film className="h-5 w-5" style={{ color: ACCENT }} /> Production Plan</CardTitle>
            <CardDescription>{scenes.length} scene{scenes.length === 1 ? "" : "s"} · {shots.length} shot{shots.length === 1 ? "" : "s"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <button className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
              onClick={() => setShowShots((s) => !s)} data-testid="movie-studio-toggle-shots">
              {showShots ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              {showShots ? "Hide" : "Show"} shot breakdown
            </button>
            {showShots && (
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1" data-testid="movie-studio-shot-list">
                {shots.map((s, i) => (
                  <div key={s.id} className="rounded-lg border border-border bg-background/40 p-3">
                    <p className="font-medium">{i + 1}. {s.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">{s.meta?.visual_prompt || s.description}</p>
                  </div>
                ))}
              </div>
            )}
            <Button data-testid="movie-studio-generate-jobs-btn" onClick={onGenerateJobs} disabled={genJobs.isPending}
              variant={hasJobs ? "outline" : "default"} className="gap-2" style={hasJobs ? {} : { background: ACCENT }}>
              {genJobs.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ListVideo className="h-4 w-4" />}
              {hasJobs ? "Regenerate Render Jobs" : "Generate Render Jobs"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* STEP 3 — Produce & progress */}
      {hasJobs && status && (
        <Card className="border-border/70 bg-card/60" data-testid="movie-studio-production">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-heading"><Clapperboard className="h-5 w-5" style={{ color: ACCENT }} /> Production</CardTitle>
            <CardDescription>Render every shot, then Akasha assembles the final master. Completed shots are never re-rendered.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <Button data-testid="movie-studio-produce-btn" onClick={onProduce} disabled={producing || !!finalAsset}
                className="gap-2" style={{ background: ACCENT }}>
                {producing ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
                {finalAsset ? "Movie Ready" : producing ? "Producing…" : "Produce Movie"}
              </Button>
              <span className="text-sm text-muted-foreground" data-testid="movie-studio-progress-label">{status.progress}% complete</span>
            </div>

            <Progress value={status.progress} className="h-2" data-testid="movie-studio-progress" />

            <div className="flex flex-wrap gap-2">
              <StatChip label="Total" value={status.total_jobs} testid="movie-stat-total" />
              <StatChip label="Queued" value={status.queued + status.draft} testid="movie-stat-queued" tone={status.queued + status.draft ? "active" : "muted"} />
              <StatChip label="Processing" value={status.processing + status.submitting} testid="movie-stat-processing" tone={status.processing + status.submitting ? "active" : "muted"} />
              <StatChip label="Completed" value={status.completed} testid="movie-stat-completed" tone={status.completed ? "done" : "muted"} />
              <StatChip label="Failed" value={status.failed} testid="movie-stat-failed" tone={status.failed ? "fail" : "muted"} />
            </div>

            {blocked && (
              <div className="rounded-lg border border-rose-400/30 bg-rose-400/10 px-4 py-2 text-sm text-rose-100" data-testid="movie-studio-blocked">
                Some shots failed. Retry them below, then press Produce Movie to resume.
              </div>
            )}

            {status.errors?.length > 0 && (
              <div className="space-y-1 text-sm text-rose-200" data-testid="movie-studio-errors">
                {status.errors.map((e, i) => <p key={i}>• {e.message || e.code || "Error"}</p>)}
              </div>
            )}

            {/* Per-shot job list */}
            <div className="space-y-2" data-testid="movie-studio-jobs">
              {shots.map((s, i) => {
                const job = jobByShot.get(s.id);
                const st = job?.status ?? "draft";
                const tone = JOB_TONE[st] ?? JOB_TONE.draft;
                return (
                  <div key={s.id} className="flex items-center gap-3 rounded-lg border border-border bg-background/40 px-3 py-2" data-testid={`movie-job-row-${i}`}>
                    <span className="w-6 shrink-0 text-sm text-muted-foreground">{i + 1}</span>
                    {st === "completed" ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                      : st === "failed" ? <XCircle className="h-4 w-4 shrink-0 text-rose-400" />
                      : ["processing", "submitting"].includes(st) ? <Loader2 className="h-4 w-4 shrink-0 animate-spin text-sky-400" />
                      : <Film className="h-4 w-4 shrink-0 text-muted-foreground" />}
                    <span className="min-w-0 flex-1 truncate text-sm">{s.title}</span>
                    {job?.error_message && st === "failed" && (
                      <span className="hidden max-w-[220px] truncate text-xs text-rose-300 sm:inline" title={job.error_message}>{job.error_message}</span>
                    )}
                    <Badge variant="outline" className={`shrink-0 ${tone.cls}`}>{tone.label}</Badge>
                    {st === "failed" && job && (
                      <Button size="sm" variant="outline" className="h-7 gap-1 border-rose-400/40" data-testid={`movie-retry-${i}`}
                        onClick={() => onRetry(job.id)} disabled={retry.isPending}>
                        <RotateCcw className="h-3.5 w-3.5" /> Retry
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* STEP 4 — Final master */}
      {finalAsset && (
        <Card className="border-emerald-400/30 bg-card/60" data-testid="movie-studio-final">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-heading"><CheckCircle2 className="h-5 w-5 text-emerald-400" /> Final Master</CardTitle>
            <CardDescription>Your movie is assembled and ready to view.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <video key={finalAsset} controls className="w-full rounded-xl border border-border bg-black"
              src={fileUrl(finalAsset)} data-testid="movie-studio-video" />
            <div className="flex flex-wrap gap-3">
              <a href={fileUrl(finalAsset)} download data-testid="movie-studio-download">
                <Button className="gap-2" style={{ background: ACCENT }}><Download className="h-4 w-4" /> Download MP4</Button>
              </a>
              {status?.subtitle_asset_id && (
                <a href={fileUrl(status.subtitle_asset_id)} download data-testid="movie-studio-subtitles">
                  <Button variant="outline" className="gap-2"><Captions className="h-4 w-4" /> Subtitles (.srt)</Button>
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
