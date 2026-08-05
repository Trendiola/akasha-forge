import { useRef, useState } from "react";
import type React from "react";
import { toast } from "sonner";
import { Upload, Eraser, Layers, Brush, Maximize, Scaling, Play, ImageIcon, Wand2 } from "lucide-react";
import { fileUrl, uploadFile } from "@/lib/api";
import { useImageOperations, useImageJobs, useCreateImageJob } from "@/features/imageEdit/hooks";
import { useCreateForgeItem } from "@/features/forge/hooks";
import { useProviders } from "@/features/providers/hooks";
import { ProviderRequired } from "@/components/forge/ProviderRequired";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const ICONS: Record<string, any> = {
  object_removal: Eraser, background_replacement: Layers, inpainting: Brush, outpainting: Maximize, upscaling: Scaling,
};

export function ImageEditor({ projectId, accent = "#EC4899" }: { projectId?: string | null; accent?: string }) {
  const { data: ops = [] } = useImageOperations();
  const { data: jobs = [] } = useImageJobs(projectId);
  const createJob = useCreateImageJob();
  const createAsset = useCreateForgeItem(projectId ?? "", "image");
  const { data: imageProviders = [] } = useProviders("image");
  const hasProvider = imageProviders.some((p) => p.enabled);
  const fileRef = useRef<HTMLInputElement>(null);
  const [source, setSource] = useState<{ id: string; url: string } | null>(null);
  const [op, setOp] = useState<string>("");
  const [prompt, setPrompt] = useState("");

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    toast.info("Uploading…");
    try {
      const res = await uploadFile(file, "image-edit");
      setSource({ id: res.id, url: res.url });
      if (projectId) {
        await createAsset.mutateAsync({ kind: "asset", title: file.name, data: { file_id: res.id, url: res.url, source: "upload" } });
      }
      toast.success("Image loaded and saved to Gallery");
    } catch { toast.error("Upload failed. Please try again."); }
    e.target.value = "";
  };

  const run = async () => {
    if (!source) return toast.error("Upload a source image first");
    if (!op) return toast.error("Select an operation");
    try {
      const job = await createJob.mutateAsync({ operation: op, source_file_id: source.id, project_id: projectId });
      if (job.status === "error") toast.error(job.message);
      else toast.success(`Queued ${op.replace("_", " ")} on ${job.provider_name || "provider"}`);
    } catch { toast.error("Could not queue operation."); }
  };

  const generate = async () => {
    if (!hasProvider) return toast.error("Enable an image provider to generate. No fake generation is performed.");
    if (!prompt.trim()) return toast.error("Enter a prompt");
    if (projectId) {
      await createAsset.mutateAsync({ kind: "asset", title: prompt.slice(0, 40), data: { prompt, status: "queued", source: "generate" } });
    }
    toast.success("Generation queued — will run on the enabled provider");
    setPrompt("");
  };

  return (
    <div className="space-y-4" data-testid="image-editor">
      <ProviderRequired category="image" action="AI generation and editing" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <div className="flex items-center justify-center rounded-2xl border border-dashed border-border bg-card/40" style={{ minHeight: 280 }}>
            {source ? (
              <img src={fileUrl(source.id)} alt="source" className="max-h-[360px] rounded-xl object-contain" data-testid="canvas-image" />
            ) : (
              <div className="flex flex-col items-center gap-3 py-10 text-center">
                <ImageIcon className="h-10 w-10 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Upload a source image to begin</p>
                <Button variant="outline" className="gap-2" onClick={() => fileRef.current?.click()} data-testid="image-upload-btn"><Upload className="h-4 w-4" /> Upload image</Button>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
          </div>

          <div className="rounded-2xl border border-border bg-card/50 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Generate from prompt</p>
            <div className="flex items-end gap-2">
              <Textarea rows={2} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Describe the image…" data-testid="generate-prompt-input" />
              <Button className="h-[52px] gap-2" style={{ background: accent }} onClick={generate} data-testid="generate-btn"><Wand2 className="h-4 w-4" /> Generate</Button>
            </div>
          </div>

          {source && (
            <div className="flex items-center justify-between">
              <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => fileRef.current?.click()}><Upload className="h-3.5 w-3.5" /> Replace</Button>
              <Button className="gap-2" onClick={run} disabled={createJob.isPending} style={{ background: accent }} data-testid="image-run-btn"><Play className="h-4 w-4" /> Run operation</Button>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Operations</p>
            <div className="grid grid-cols-2 gap-2">
              {ops.map((o: any) => {
                const Icon = ICONS[o.id] ?? Brush;
                return (
                  <button key={o.id} onClick={() => setOp(o.id)} data-testid={`image-op-${o.id}`}
                    className={cn("flex flex-col items-start gap-2 rounded-xl border p-3 text-left transition-all", op === o.id ? "border-primary bg-primary/10" : "border-border bg-card/50 hover:border-primary/40")}>
                    <Icon className="h-4 w-4" style={{ color: accent }} />
                    <span className="text-xs font-medium leading-tight">{o.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Edit Queue</p>
            {jobs.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">No jobs yet</p>
            ) : (
              <div className="space-y-2">
                {jobs.slice(0, 8).map((j: any) => (
                  <div key={j.id} className="flex items-center gap-2 rounded-lg border border-border bg-card/50 px-3 py-2 text-xs" data-testid="image-job-row">
                    <span className="flex-1 capitalize">{j.operation.replace("_", " ")}</span>
                    <Badge variant="outline" className={cn("text-[10px]", j.status === "error" ? "text-red-400" : "text-amber-400")}>{j.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
