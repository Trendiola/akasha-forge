import {
  Search,
  Bell,
  Command as CmdIcon,
  Sparkles,
  ChevronDown,
} from "lucide-react";
import { useApp } from "@/store/app-context";
import { ProjectSelector } from "@/features/projects/ProjectSelector";
import { AiStatus } from "./AiStatus";
import { ThemeToggle } from "./ThemeToggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function TopBar() {
  const { setCommandOpen } = useApp();

  return (
    <header
      className="relative z-10 flex h-[64px] shrink-0 items-center gap-3 border-b border-white/[0.055] bg-[hsl(var(--background)/0.7)] px-5 backdrop-blur-2xl"
      data-testid="topbar"
    >
      {/* subtle top energy line */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent"
      />

      {/* Current project */}
      <div className="flex min-w-0 items-center">
        <ProjectSelector />
      </div>

      {/* Global command search */}
      <button
        onClick={() => setCommandOpen(true)}
        data-testid="global-search"
        className="akasha-search group mx-auto flex h-9 min-w-[240px] max-w-[500px] flex-1 items-center gap-2.5 rounded-lg px-3.5 text-sm text-white/42 outline-none"
      >
        <Search className="h-4 w-4 shrink-0 transition-colors group-hover:text-violet-300" />

        <span className="flex-1 truncate text-left text-[12px]">
          Search projects, assets, Forges and commands...
        </span>

        <div className="flex items-center gap-1.5">
          <span className="hidden text-[9px] font-medium uppercase tracking-[0.13em] text-white/20 xl:inline">
            Command
          </span>

          <kbd className="flex h-6 items-center gap-0.5 rounded-md border border-white/[0.08] bg-white/[0.035] px-1.5 font-mono text-[9px] text-white/38 shadow-inner">
            <CmdIcon className="h-2.5 w-2.5" />
            K
          </kbd>
        </div>
      </button>

      {/* Right controls */}
      <div className="ml-auto flex shrink-0 items-center gap-1.5">
        {/* AI system state */}
        <div className="hidden items-center gap-2 rounded-xl border border-white/[0.055] bg-white/[0.025] px-2 py-1 lg:flex">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/[0.09]">
            <Sparkles className="h-3.5 w-3.5 text-violet-300" />
          </div>

          <AiStatus />
        </div>

        <ThemeToggle />

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative h-9 w-9 rounded-xl text-white/45 hover:bg-white/[0.045] hover:text-white"
              data-testid="notifications-btn"
            >
              <Bell className="h-[17px] w-[17px]" />

              <span className="absolute right-[8px] top-[8px] h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_hsl(var(--akasha)/0.85)]" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            align="end"
            className="glass-strong w-72 border-white/[0.08]"
          >
            <DropdownMenuLabel>
              <div>
                <p className="text-sm font-semibold text-white">
                  Notifications
                </p>
                <p className="mt-0.5 text-[10px] font-normal text-white/35">
                  System and creative activity
                </p>
              </div>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <div className="px-3 py-7 text-center">
              <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-xl border border-primary/10 bg-primary/[0.055]">
                <Bell className="h-3.5 w-3.5 text-violet-300/70" />
              </div>

              <p className="text-xs text-white/45">
                You're all caught up.
              </p>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Divider */}
        <div className="mx-1 h-6 w-px bg-white/[0.06]" />

        {/* Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              data-testid="user-profile"
              className="group flex items-center gap-2 rounded-xl p-1 pr-1.5 outline-none transition-colors hover:bg-white/[0.035] focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <Avatar className="h-8 w-8 border border-primary/20 shadow-[0_0_18px_hsl(var(--akasha)/0.08)]">
                <AvatarFallback className="bg-gradient-to-br from-primary/25 to-violet-950 text-[10px] font-bold text-violet-200">
                  AF
                </AvatarFallback>
              </Avatar>

              <div className="hidden text-left xl:block">
                <p className="max-w-[90px] truncate text-[10px] font-semibold leading-none text-white/75">
                  Creator
                </p>
                <p className="mt-1 text-[8px] uppercase tracking-[0.12em] text-white/25">
                  Studio
                </p>
              </div>

              <ChevronDown className="hidden h-3 w-3 text-white/25 transition-transform group-data-[state=open]:rotate-180 xl:block" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent
            align="end"
            className="glass-strong w-56 border-white/[0.08]"
          >
            <DropdownMenuLabel>
              <p className="text-sm font-medium text-white">Creator</p>
              <p className="mt-0.5 text-[10px] font-normal text-white/35">
                Local workspace
              </p>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Preferences</DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem>Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
