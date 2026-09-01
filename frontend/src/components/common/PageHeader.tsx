import React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  icon?: React.ElementType;
  title: string;
  tagline?: string;
  description?: string;
  accent?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  icon: Icon,
  title,
  tagline,
  description,
  accent = "#6D3BFF",
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("relative mb-5 flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.055] pb-5", className)}>
      <div className="flex items-start gap-4">
        {Icon && (
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-white/[0.08]"
            style={{
              background: `linear-gradient(140deg, ${accent}22, transparent)`,
              boxShadow: `0 0 24px -8px ${accent}66`,
            }}
          >
            <Icon className="h-6 w-6" style={{ color: accent }} />
          </div>
        )}
        <div>
          {tagline && (
            <p
              className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em]"
              style={{ color: accent }}
            >
              {tagline}
            </p>
          )}
          <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
