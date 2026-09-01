import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Sparkles,
  PanelLeftClose,
  PanelLeft,
  Orbit,
} from "lucide-react";
import { NAV_SECTIONS, getModule } from "@/config/modules";
import { useApp } from "@/store/app-context";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useApp();
  const width = sidebarCollapsed ? 76 : 276;

  return (
    <motion.aside
      animate={{ width }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      className="relative z-20 flex h-full shrink-0 flex-col overflow-hidden border-r border-white/[0.06] bg-[hsl(var(--sidebar)/0.88)] backdrop-blur-2xl"
      data-testid="sidebar"
    >
      {/* Ambient Akasha energy */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-20 -top-24 h-64 w-64 rounded-full bg-primary/[0.10] blur-[90px]"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-28 -right-24 h-56 w-56 rounded-full bg-cyan-400/[0.04] blur-[90px]"
      />

      {/* Brand */}
      <div
        className={cn(
          "relative flex h-[82px] shrink-0 items-center border-b border-white/[0.055]",
          sidebarCollapsed ? "justify-center px-3" : "gap-3.5 px-4"
        )}
      >
        <div className="akasha-brand-mark flex h-10 w-10 shrink-0 items-center justify-center rounded-xl">
          <Sparkles className="relative z-10 h-[19px] w-[19px] text-white" />
        </div>

        {!sidebarCollapsed && (
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="truncate font-display text-[14px] font-bold leading-none tracking-[-0.02em] text-white">
                AKASHA FORGE
              </p>

              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-300 shadow-[0_0_10px_rgba(103,232,249,0.75)]" />
            </div>

            <p className="mt-1.5 truncate text-[9px] font-medium uppercase tracking-[0.17em] text-white/35">
              The Creative Operating System
            </p>
          </div>
        )}
      </div>

      {/* System identity */}
      {!sidebarCollapsed && (
        <div className="relative mx-3 mt-3 overflow-hidden rounded-xl border border-primary/[0.12] bg-primary/[0.045] px-3 py-2.5">
          <div className="absolute inset-y-0 left-0 w-[2px] bg-gradient-to-b from-primary via-violet-400 to-cyan-300" />

          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
              <Orbit className="h-3.5 w-3.5 text-violet-300" />
            </div>

            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-white/70">
                Akasha System
              </p>
              <p className="mt-0.5 text-[9px] text-white/30">
                Creative workspace ready
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="relative flex-1 overflow-y-auto px-3 pb-4 pt-4">
        <TooltipProvider delayDuration={0}>
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-5">
              {!sidebarCollapsed && (
                <div className="mb-2 flex items-center gap-2 px-2">
                  <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-white/28">
                    {section.title}
                  </p>
                  <div className="h-px flex-1 bg-gradient-to-r from-white/[0.07] to-transparent" />
                </div>
              )}

              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;

                  const moduleAccent = item.moduleId
                    ? getModule(item.moduleId)?.accent
                    : undefined;

                  const link = (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      end={item.path === "/"}
                      data-testid={`nav-${item.label
                        .toLowerCase()
                        .replace(/\s+/g, "-")}`}
                      className={({ isActive }) =>
                        cn(
                          "group relative flex min-h-[40px] items-center gap-3 overflow-hidden rounded-xl px-3 text-[13px] font-medium outline-none transition-all duration-200",
                          sidebarCollapsed && "justify-center px-0",
                          isActive
                            ? "akasha-active text-white"
                            : "text-white/48 hover:bg-white/[0.045] hover:text-white/88"
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <>
                              <motion.span
                                layoutId="akasha-sidebar-active"
                                className="absolute inset-y-2 left-0 w-[3px] rounded-r-full bg-primary shadow-[0_0_14px_hsl(var(--akasha)/0.85)]"
                                transition={{
                                  type: "spring",
                                  stiffness: 350,
                                  damping: 32,
                                }}
                              />

                              <span className="pointer-events-none absolute inset-0 bg-gradient-to-r from-primary/[0.07] via-transparent to-transparent" />
                            </>
                          )}

                          <span
                            className={cn(
                              "relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-all duration-200",
                              isActive
                                ? "bg-primary/[0.13]"
                                : "bg-transparent group-hover:bg-white/[0.035]"
                            )}
                            style={
                              isActive && moduleAccent
                                ? {
                                    color: moduleAccent,
                                    boxShadow: `0 0 18px ${moduleAccent}20`,
                                  }
                                : undefined
                            }
                          >
                            <Icon
                              className={cn(
                                "h-[17px] w-[17px] transition-transform duration-200",
                                !isActive && "group-hover:scale-105"
                              )}
                            />
                          </span>

                          {!sidebarCollapsed && (
                            <span className="relative z-10 truncate">
                              {item.label}
                            </span>
                          )}

                          {!sidebarCollapsed && isActive && (
                            <span className="relative z-10 ml-auto h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_9px_hsl(var(--akasha)/0.8)]" />
                          )}
                        </>
                      )}
                    </NavLink>
                  );

                  return sidebarCollapsed ? (
                    <Tooltip key={item.path}>
                      <TooltipTrigger asChild>{link}</TooltipTrigger>
                      <TooltipContent
                        side="right"
                        className="glass-strong border-white/10 text-xs"
                      >
                        {item.label}
                      </TooltipContent>
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

      {/* Footer / collapse */}
      <div className="relative border-t border-white/[0.055] bg-black/[0.08]">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2 px-5 pt-3">
            <span className="akasha-status-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="text-[9px] font-medium uppercase tracking-[0.13em] text-white/30">
              Local Workspace
            </span>
          </div>
        )}

        <button
          onClick={toggleSidebar}
          data-testid="sidebar-toggle"
          className={cn(
            "flex h-12 w-full items-center gap-3 px-5 text-white/35 outline-none transition-colors hover:bg-white/[0.025] hover:text-white/75",
            sidebarCollapsed && "justify-center px-0"
          )}
        >
          {sidebarCollapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}

          {!sidebarCollapsed && (
            <span className="text-[11px] font-medium">Collapse sidebar</span>
          )}
        </button>
      </div>
    </motion.aside>
  );
}