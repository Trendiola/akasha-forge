import React from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ElementType;
  title: string;
  description?: string;
  accent?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  accent = "#6D3BFF",
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "akasha-panel flex min-h-[260px] flex-col items-center justify-center rounded-xl border-dashed px-6 py-12 text-center",
        className
      )}
      data-testid="empty-state"
    >
      {Icon && (
        <div
          className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl"
          style={{ background: `${accent}18` }}
        >
          <Icon className="h-8 w-8" style={{ color: accent }} />
        </div>
      )}
      <h3 className="font-heading text-lg font-bold">{title}</h3>
      {description && (
        <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
