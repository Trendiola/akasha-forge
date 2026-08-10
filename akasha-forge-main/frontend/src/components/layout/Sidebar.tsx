import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, PanelLeftClose, PanelLeft } from "lucide-react";
import { NAV_SECTIONS } from "@/config/modules";
import { useApp } from "@/store/app-context";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useApp();
  const width = sidebarCollapsed ? 76 : 268;

  return (
    <motion.aside
      animate={{ width }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      className="relative z-20 flex h-full flex-col border-r border-border bg-[hsl(var(--sidebar))]"
      data-testid="sidebar"
    >
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary akasha-glow">
          <Sparkles className="h-5 w-5 text-primary-foreground" />
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <p className="truncate font-display text-sm font-bold leading-none tracking-tight">
              Akasha Forge
            </p>
            <p className="mt-1 truncate text-[11px] text-muted-foreground">
              The Creative OS
            </p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        <TooltipProvider delayDuration={0}>
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-5">
              {!sidebarCollapsed && (
                <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
                  {section.title}
                </p>
              )}
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const link = (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === "/"}
                      data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
                      className={({ isActive }) =>
                        cn(
                          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                          sidebarCollapsed && "justify-center px-0",
                          isActive
                            ? "bg-accent text-foreground"
                            : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary" />
                          )}
                          <Icon className="h-[18px] w-[18px] shrink-0" />
                          {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                        </>
                      )}
                    </NavLink>
                  );
                  return sidebarCollapsed ? (
                    <Tooltip key={item.path}>
                      <TooltipTrigger asChild>{link}</TooltipTrigger>
                      <TooltipContent side="right">{item.label}</TooltipContent>
                    </Tooltip>
                  ) : (
                    link
                  );
                })}
              </div>
            </div>
          ))}
        </TooltipProvider>
      </nav>

      {/* Collapse */}
      <button
        onClick={toggleSidebar}
        data-testid="sidebar-toggle"
        className="flex h-12 items-center gap-3 border-t border-border px-5 text-muted-foreground transition-colors hover:text-foreground"
      >
        {sidebarCollapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        {!sidebarCollapsed && <span className="text-xs">Collapse</span>}
      </button>
    </motion.aside>
  );
}
