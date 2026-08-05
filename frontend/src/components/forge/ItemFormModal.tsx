import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

export interface ForgeField {
  name: string;
  label: string;
  type: "text" | "textarea" | "number" | "switch" | "select";
  options?: { value: string; label: string }[];
  required?: boolean;
  placeholder?: string;
}

export interface ForgeSchema {
  kind: string;
  singular: string;
  titleField: string;
  fields: ForgeField[];
}

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  schema: ForgeSchema;
  accent?: string;
  initial?: { id?: string; title?: string; data?: Record<string, any> } | null;
  onSubmit: (payload: { title: string; data: Record<string, any> }) => Promise<void>;
}

export function ItemFormModal({ open, onOpenChange, schema, accent = "#6D3BFF", initial, onSubmit }: Props) {
  const [values, setValues] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const isEdit = !!initial?.id;

  useEffect(() => {
    if (open) {
      const base: Record<string, any> = { ...(initial?.data ?? {}) };
      if (initial?.title !== undefined) base[schema.titleField] = initial.title;
      schema.fields.forEach((f) => { if (base[f.name] === undefined) base[f.name] = f.type === "switch" ? false : ""; });
      setValues(base);
    }
  }, [open, initial, schema]);

  const set = (name: string, v: any) => setValues((s) => ({ ...s, [name]: v }));

  const submit = async () => {
    const titleVal = String(values[schema.titleField] ?? "").trim();
    if (!titleVal) return toast.error(`${schema.fields.find((f) => f.name === schema.titleField)?.label ?? "Title"} is required`);
    for (const f of schema.fields) {
      if (f.required && !String(values[f.name] ?? "").trim()) return toast.error(`${f.label} is required`);
    }
    const data: Record<string, any> = { ...values };
    delete data[schema.titleField];
    setSaving(true);
    try {
      await onSubmit({ title: titleVal, data });
      onOpenChange(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(detail ? `Could not save: ${detail}` : "Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-strong sm:max-w-lg" data-testid="forge-item-modal">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">{isEdit ? "Edit" : "New"} {schema.singular}</DialogTitle>
          <DialogDescription>Fields are saved to the project and persist in MongoDB.</DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] space-y-4 overflow-y-auto py-2 pr-1">
          {schema.fields.map((f) => (
            <div key={f.name} className={f.type === "switch" ? "flex items-center justify-between rounded-lg border border-border bg-card/50 px-3 py-2.5" : "space-y-1.5"}>
              <Label>{f.label}</Label>
              {f.type === "textarea" ? (
                <Textarea rows={4} value={values[f.name] ?? ""} placeholder={f.placeholder} onChange={(e) => set(f.name, e.target.value)} data-testid={`field-${f.name}`} />
              ) : f.type === "number" ? (
                <Input type="number" value={values[f.name] ?? ""} placeholder={f.placeholder} onChange={(e) => set(f.name, e.target.value === "" ? "" : Number(e.target.value))} data-testid={`field-${f.name}`} />
              ) : f.type === "switch" ? (
                <Switch checked={!!values[f.name]} onCheckedChange={(v) => set(f.name, v)} data-testid={`field-${f.name}`} />
              ) : f.type === "select" ? (
                <Select value={values[f.name] ?? ""} onValueChange={(v) => set(f.name, v)}>
                  <SelectTrigger data-testid={`field-${f.name}`}><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent>{(f.options ?? []).map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
                </Select>
              ) : (
                <Input value={values[f.name] ?? ""} placeholder={f.placeholder} onChange={(e) => set(f.name, e.target.value)} autoFocus={f.name === schema.titleField} data-testid={`field-${f.name}`} />
              )}
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={saving} style={{ background: accent }} data-testid="forge-item-submit">
            {saving ? "Saving…" : isEdit ? "Save changes" : `Create ${schema.singular}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
