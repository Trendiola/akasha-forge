import { useRef, useState } from "react";
import type React from "react";
import { toast } from "sonner";
import { Upload, Eraser, Layers, Brush, Maximize, Scaling, Play, ImageIcon } from "lucide-react";
import { fileUrl, uploadFile } from "@/lib/api";
import { useImageOperations, useImageJobs, useCreateImageJob } from "@/features/imageEdit/hooks";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const ICONS: Record<string, any> = {
  object_removal: Eraser, background_replacement: Layers, inpainting: Brush, outpainting: Maximize, upscaling: Scaling,
};

export function ImageEditor({ projectId, accent = "#EC4899" }: { projectId?: string | null; accent?: string }) {
  const { data: ops = [] } = useImageOperations();
  const { data: jobs = [] } = useImageJobs(projectId);
  const createJob = useCreateImageJob();
  const fileRef = useRef<HTMLInputElement>(null);
  const [source, setSource] = useState<{ id: string; url: string } | null>(null);
  const [op, setOp] = useState<string>("");

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    toast.info("Uploading…");
    try {
      const res = await uploadFile(file, "image-edit");
      setSource({ id: res.id, url: res.url });
      toast.success("Source loaded");
    } catch { toast.error("Upload failed"); }
    e.target.value = "";
  };

  const run = async () => {
    if (!source) return toast.error("Upload a source image first");
    if (!op) return toast.error("Select an operation");
    const job = await createJob.mutateAsync({ operation: op, source_file_id: source.id, project_id: projectId });
    if (job.status === "error") toast.error(job.message);
    else toast.success(`Queued ${op.replace("_", " ")} on ${job.provider_name || "provider"}`);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]" data-testid="image-editor">
      <div className="space-y-4">
        <div className="flex items-center justify-center rounded-2xl border border-dashed border-border bg-card/40" style={{ minHeight: 280 }}>
          {source ? (
            <img src={fileUrl(source.id)} alt="source" className="max-h-[360px] rounded-xl object-contain" />
          ) : (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <ImageIcon className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Upload a source image to begin editing</p>
              <Button variant="outline" className="gap-2" onClick={() => fileRef.current?.click()} data-testid="image-upload-btn">
                <Upload className="h-4 w-4" /> Upload image
              </Button>
            </div>
          )}
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
        </div>
        {source && (
          <div className="flex items-center justify-between">
            <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => fileRef.current?.click()}><Upload className="h-3.5 w-3.5" /> Replace</Button>
            <Button className="gap-2" onClick={run} disabled={createJob.isPending} style={{ background: accent }} data-testid="image-run-btn">
              <Play className="h-4 w-4" /> Run operation
            </Button>
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
  );
}
