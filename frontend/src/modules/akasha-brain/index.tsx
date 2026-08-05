import { useState } from "react";
import { toast } from "sonner";
import { Sparkles, Send, Wand2, Copy, Cpu, Activity } from "lucide-react";
import { getModule } from "@/config/modules";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useBrainStatus, useOptimizePrompt, useAssist } from "@/features/brain/hooks";
import { useActiveProject } from "@/features/projects/useActiveProject";

const TARGETS = ["image", "video", "text", "music", "voice"];

export default function AkashaBrain() {
  const mod = getModule("akasha-brain");
  const project = useActiveProject();
  const { data: status } = useBrainStatus();
  const optimize = useOptimizePrompt();
  const assist = useAssist();

  const [raw, setRaw] = useState("");
  const [target, setTarget] = useState("image");
  const [optimized, setOptimized] = useState("");
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");

  const runOptimize = async () => {
    if (!raw.trim()) return toast.error("Enter a prompt idea first");
    try {
      const res = await optimize.mutateAsync({ prompt: raw, target, project_id: project?.id ?? null });
      setOptimized(res.optimized);
      toast.success(res.used_context ? "Optimized with project context" : "Prompt optimized");
    } catch { toast.error("Akasha Brain is unavailable"); }
  };

  const runAssist = async () => {
    if (!message.trim()) return;
    try {
      const res = await assist.mutateAsync({ message, project_id: project?.id ?? null });
      setReply(res.reply);
    } catch { toast.error("Akasha Brain is unavailable"); }
  };

  return (
    <div className="animate-in fade-in duration-500" data-testid="module-akasha-brain">
      <PageHeader icon={mod.icon} title={mod.label} tagline={mod.tagline} description={mod.description} accent={mod.accent} />

      <Tabs defaultValue="command">
        <TabsList className="mb-6 bg-secondary/40 p-1">
          {mod.tabs.map((t) => <TabsTrigger key={t.id} value={t.id} className="data-[state=active]:bg-background" data-testid={`brain-tab-${t.id}`}>{t.label}</TabsTrigger>)}
        </TabsList>

        <TabsContent value="command" className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard icon={Cpu} label="Model" value={<span className="text-base">{status?.model?.split("/")[1] ?? "—"}</span>} hint="Reasoning engine" />
            <StatCard icon={Activity} label="Brain" value={status?.online ? "Online" : "Offline"} hint="LLM connectivity" accent="#22C55E" />
            <StatCard icon={Sparkles} label="Providers" value={`${status?.providers_enabled ?? 0}/${status?.providers_total ?? 0}`} hint="Enabled engines" accent="#0EA5E9" />
            <StatCard icon={Wand2} label="Context" value={project ? "Loaded" : "None"} hint={project?.name ?? "No project"} accent="#A855F7" />
          </div>
          <div className="rounded-2xl border border-border bg-card/50 p-5">
            <h3 className="mb-4 font-heading font-bold">Engine coverage by category</h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {status?.categories && Object.entries(status.categories).map(([cat, v]: any) => (
                <div key={cat} className="rounded-xl border border-border bg-background/40 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{cat}</p>
                  <p className="mt-1 font-display text-xl font-bold">{v.enabled}<span className="text-sm text-muted-foreground">/{v.total}</span></p>
                  <p className="text-[11px] text-emerald-400">{v.ready} ready</p>
                </div>
              ))}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="optimizer" className="space-y-4">
          <div className="flex items-center gap-3">
            <Select value={target} onValueChange={setTarget}>
              <SelectTrigger className="w-40" data-testid="optimizer-target"><SelectValue /></SelectTrigger>
              <SelectContent>{TARGETS.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}</SelectContent>
            </Select>
            {project && <Badge variant="outline" className="gap-1"><Sparkles className="h-3 w-3 text-primary" /> Using {project.name} context</Badge>}
          </div>
          <Textarea rows={4} value={raw} onChange={(e) => setRaw(e.target.value)} placeholder="Describe your raw idea… e.g. 'a lone knight at dawn'" data-testid="optimizer-input" />
          <Button onClick={runOptimize} disabled={optimize.isPending} className="gap-2" data-testid="optimizer-run">
            <Wand2 className="h-4 w-4" /> {optimize.isPending ? "Optimizing…" : "Optimize prompt"}
          </Button>
          {optimized && (
            <div className="rounded-2xl border border-primary/30 bg-card/50 p-5 akasha-glow" data-testid="optimizer-output">
              <div className="mb-2 flex items-center justify-between">
                <p className="font-heading text-sm font-bold text-primary">Optimized prompt</p>
                <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => { navigator.clipboard.writeText(optimized); toast.success("Copied"); }}>
                  <Copy className="h-3.5 w-3.5" /> Copy
                </Button>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{optimized}</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="assistant" className="space-y-4">
          {reply && (
            <div className="rounded-2xl border border-border bg-card/50 p-5" data-testid="assistant-output">
              <p className="mb-2 font-heading text-sm font-bold text-primary">Akasha Brain</p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{reply}</p>
            </div>
          )}
          <div className="flex items-end gap-2">
            <Textarea rows={2} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Ask about story, characters, world-building, workflow…" data-testid="assistant-input" />
            <Button onClick={runAssist} disabled={assist.isPending} size="icon" className="h-[52px] w-[52px] shrink-0" data-testid="assistant-run">
              <Send className="h-5 w-5" />
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
