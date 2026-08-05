import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useCreateProject } from "./hooks";
import { useApp } from "@/store/app-context";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const TYPES = [
  { value: "story", label: "Story / Novel" },
  { value: "film", label: "Film / Series" },
  { value: "game", label: "Game" },
  { value: "album", label: "Album" },
  { value: "book", label: "Book" },
];

const COLORS = ["#6D3BFF", "#A855F7", "#EC4899", "#F43F5E", "#0EA5E9", "#14B8A6", "#22C55E", "#EAB308"];

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function CreateProjectDialog({ open, onOpenChange }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("story");
  const [color, setColor] = useState(COLORS[0]);
  const create = useCreateProject();
  const { setActiveProjectId } = useApp();
  const navigate = useNavigate();

  const submit = async () => {
    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }
    try {
      const project = await create.mutateAsync({ name: name.trim(), description, type, color });
      if (!project?.id) {
        throw new Error("Server did not return a project id");
      }
      setActiveProjectId(project.id);
      toast.success(`“${project.name}” created`);
      setName("");
      setDescription("");
      onOpenChange(false);
      navigate("/");
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      toast.error(
        detail
          ? `Could not create project: ${detail}`
          : status
            ? `Could not create project (error ${status}). Please try again.`
            : "Could not create project. Please check your connection and try again."
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong sm:max-w-lg" data-testid="create-project-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">Create a project</DialogTitle>
          <DialogDescription>
            Every Forge works within a project — its own Story, Character and World bibles.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="p-name">Name</Label>
            <Input
              id="p-name"
              data-testid="project-name-input"
              placeholder="Untitled Universe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-desc">Description</Label>
            <Textarea
              id="p-desc"
              data-testid="project-desc-input"
              placeholder="A short logline for your world…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger data-testid="project-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Accent</Label>
              <div className="flex flex-wrap gap-2 pt-1.5">
                {COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setColor(c)}
                    style={{ background: c }}
                    className={cn(
                      "h-6 w-6 rounded-full ring-offset-2 ring-offset-background transition-transform hover:scale-110",
                      color === c && "ring-2 ring-white"
                    )}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={create.isPending}
            data-testid="project-submit-btn"
            className="font-heading font-semibold"
          >
            {create.isPending ? "Creating…" : "Create project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
