import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Calendar as CalIcon, Youtube, Facebook, Instagram, Linkedin, Twitter, Music2, Megaphone, ListChecks } from "lucide-react";
import { usePlatforms, useCampaigns, useCreateCampaign, useUpdateCampaign, useDeleteCampaign, usePosts, useCreatePost, useUpdatePost, useDeletePost } from "@/features/publish/hooks";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

const PLATFORM_META: Record<string, { icon: any; color: string }> = {
  youtube: { icon: Youtube, color: "#FF0000" }, facebook: { icon: Facebook, color: "#1877F2" },
  instagram: { icon: Instagram, color: "#E4405F" }, tiktok: { icon: Music2, color: "#00F2EA" },
  linkedin: { icon: Linkedin, color: "#0A66C2" }, x: { icon: Twitter, color: "#fff" },
};

function PlatformIcon({ p }: { p: string }) {
  const m = PLATFORM_META[p] ?? { icon: Megaphone, color: "#888" };
  return <m.icon className="h-3.5 w-3.5" style={{ color: m.color }} />;
}

export function CampaignManager() {
  const { data: campaigns = [] } = useCampaigns();
  const create = useCreateCampaign();
  const update = useUpdateCampaign();
  const del = useDeleteCampaign();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<any | null>(null);
  const [editName, setEditName] = useState("");

  const openEdit = (c: any) => { setEditing(c); setEditName(c.name); };
  const saveEdit = async () => {
    if (!editName.trim()) return toast.error("Name required");
    try {
      await update.mutateAsync({ id: editing.id, name: editName.trim(), goal: editing.goal, color: editing.color });
      toast.success("Campaign saved");
      setEditing(null);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Could not save campaign. Please try again.");
    }
  };

  return (
    <div className="space-y-4" data-testid="campaign-manager">
      <div className="flex gap-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New campaign name…" data-testid="campaign-name-input" />
        <Button className="gap-1.5" onClick={async () => { if (!name.trim()) return; try { await create.mutateAsync({ name: name.trim() }); setName(""); toast.success("Campaign created"); } catch (e: any) { toast.error(e?.response?.data?.detail ?? "Could not create campaign. Please try again."); } }} data-testid="campaign-create-btn">
          <Plus className="h-4 w-4" /> Create
        </Button>
      </div>
      {campaigns.length === 0 ? (
        <EmptyState icon={Megaphone} title="No campaigns" description="Group posts into campaigns to coordinate a launch." />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {campaigns.map((c: any) => (
            <div key={c.id} className="cursor-pointer rounded-xl border border-border bg-card/50 p-4 transition-colors hover:border-primary/40" data-testid={`campaign-card-${c.id}`} onClick={() => openEdit(c)}>
              <div className="flex items-center justify-between">
                <span className="h-3 w-3 rounded" style={{ background: c.color }} />
                <button onClick={(e) => { e.stopPropagation(); del.mutate(c.id); toast.success("Campaign deleted"); }} className="text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></button>
              </div>
              <p className="mt-3 font-heading font-semibold">{c.name}</p>
              <Badge variant="outline" className="mt-2 text-[10px] capitalize">{c.status}</Badge>
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!editing} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent className="glass-strong sm:max-w-md" data-testid="campaign-edit-dialog">
          <DialogHeader>
            <DialogTitle className="font-display text-xl">Edit campaign</DialogTitle>
            <DialogDescription>Rename your campaign. Changes persist immediately.</DialogDescription>
          </DialogHeader>
          <div className="py-2 space-y-1.5">
            <Label>Name</Label>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} data-testid="campaign-edit-input" autoFocus />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={saveEdit} disabled={update.isPending} data-testid="campaign-edit-save">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function SchedulerDialog({ open, onOpenChange, defaultDate, editing }: { open: boolean; onOpenChange: (v: boolean) => void; defaultDate?: string; editing?: any | null }) {
  const { data: platforms = [] } = usePlatforms();
  const create = useCreatePost();
  const update = useUpdatePost();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [date, setDate] = useState(defaultDate ?? "");

  useEffect(() => {
    if (open) {
      setTitle(editing?.title ?? "");
      setContent(editing?.content ?? "");
      setSelected(editing?.platforms ?? []);
      setDate(editing?.scheduled_at ?? defaultDate ?? "");
    }
  }, [open, editing, defaultDate]);

  const toggle = (p: string) => setSelected((s) => (s.includes(p) ? s.filter((x) => x !== p) : [...s, p]));

  const submit = async () => {
    if (!title.trim()) return toast.error("Title required");
    try {
      if (editing) {
        await update.mutateAsync({ id: editing.id, title: title.trim(), content, platforms: selected, scheduled_at: date });
        toast.success("Post saved");
      } else {
        await create.mutateAsync({ title: title.trim(), content, platforms: selected, scheduled_at: date });
        toast.success("Post scheduled");
      }
      setTitle(""); setContent(""); setSelected([]); onOpenChange(false);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Could not save post. Please try again.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong sm:max-w-lg" data-testid="scheduler-dialog">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">{editing ? "Edit post" : "Schedule a post"}</DialogTitle>
          <DialogDescription>Compose once, publish across channels. Connect accounts later.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5"><Label>Title</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="post-title-input" /></div>
          <div className="space-y-1.5"><Label>Content</Label><Textarea rows={3} value={content} onChange={(e) => setContent(e.target.value)} /></div>
          <div className="space-y-1.5">
            <Label>Platforms</Label>
            <div className="flex flex-wrap gap-2">
              {platforms.map((p: string) => (
                <button key={p} onClick={() => toggle(p)} data-testid={`platform-${p}`}
                  className={cn("flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs capitalize transition-colors", selected.includes(p) ? "border-primary bg-primary/10" : "border-border")}>
                  <PlatformIcon p={p} /> {p}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5"><Label>Scheduled date</Label><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid="post-date-input" /></div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={create.isPending || update.isPending} data-testid="post-schedule-btn">{editing ? "Save changes" : "Schedule"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PublishingQueue() {
  const { data: posts = [] } = usePosts();
  const del = useDeletePost();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);

  const openNew = () => { setEditing(null); setOpen(true); };
  const openEdit = (p: any) => { setEditing(p); setOpen(true); };

  return (
    <div className="space-y-4" data-testid="publishing-queue">
      <div className="flex justify-end">
        <Button className="gap-1.5" onClick={openNew} data-testid="queue-new-post"><Plus className="h-4 w-4" /> New post</Button>
      </div>
      {posts.length === 0 ? (
        <EmptyState icon={ListChecks} title="Queue is empty" description="Schedule posts to see them lined up here." />
      ) : (
        <div className="space-y-2">
          {posts.map((p: any) => (
            <div key={p.id} className="flex cursor-pointer items-center gap-3 rounded-xl border border-border bg-card/50 px-4 py-3 transition-colors hover:border-primary/40" data-testid={`queue-post-row-${p.id}`} onClick={() => openEdit(p)}>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{p.title}</p>
                <p className="text-xs text-muted-foreground">{p.scheduled_at || "Unscheduled"}</p>
              </div>
              <div className="flex gap-1">{p.platforms?.map((pl: string) => <PlatformIcon key={pl} p={pl} />)}</div>
              <Badge variant="outline" className="text-[10px] capitalize">{p.status}</Badge>
              <button onClick={(e) => { e.stopPropagation(); del.mutate(p.id); toast.success("Post deleted"); }} className="text-muted-foreground hover:text-destructive" data-testid={`queue-post-delete-${p.id}`}><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      )}
      <SchedulerDialog open={open} onOpenChange={setOpen} editing={editing} />
    </div>
  );
}

export function PublishCalendar() {
  const { data: posts = [] } = usePosts();
  const [open, setOpen] = useState(false);
  const [pickDate, setPickDate] = useState<string>("");
  const now = new Date();
  const year = now.getFullYear(), month = now.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [...Array(firstDay).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];
  const postsOn = (day: number) => {
    const d = new Date(year, month, day).toISOString().slice(0, 10);
    return posts.filter((p: any) => (p.scheduled_at || "").slice(0, 10) === d);
  };

  return (
    <div className="space-y-4" data-testid="publish-calendar">
      <div className="flex items-center justify-between">
        <h3 className="font-heading font-bold">{now.toLocaleString("default", { month: "long" })} {year}</h3>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => { setPickDate(""); setOpen(true); }}><CalIcon className="h-3.5 w-3.5" /> Schedule</Button>
      </div>
      <div className="grid grid-cols-7 gap-1.5">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => <div key={d} className="pb-1 text-center text-[11px] font-medium uppercase text-muted-foreground">{d}</div>)}
        {cells.map((day, i) => (
          <div key={i} className={cn("min-h-[84px] rounded-lg border p-1.5", day ? "border-border bg-card/40" : "border-transparent")}
            onClick={() => { if (day) { setPickDate(new Date(year, month, day).toISOString().slice(0, 10)); setOpen(true); } }}
            data-testid={day ? `calendar-day-${day}` : undefined}>
            {day && (
              <>
                <span className="text-xs text-muted-foreground">{day}</span>
                <div className="mt-1 space-y-1">
                  {postsOn(day).slice(0, 2).map((p: any) => (
                    <div key={p.id} className="truncate rounded bg-primary/15 px-1.5 py-0.5 text-[10px] text-primary">{p.title}</div>
                  ))}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      <SchedulerDialog open={open} onOpenChange={setOpen} defaultDate={pickDate} />
    </div>
  );
}
