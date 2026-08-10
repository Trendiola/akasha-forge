import { Search, Bell, Command as CmdIcon } from "lucide-react";
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
      className="glass sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-border px-6"
      data-testid="topbar"
    >
      <ProjectSelector />

      <button
        onClick={() => setCommandOpen(true)}
        data-testid="global-search"
        className="group flex h-9 min-w-[240px] max-w-md flex-1 items-center gap-2 rounded-lg border border-border bg-secondary/50 px-3 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search everything…</span>
        <kbd className="flex items-center gap-0.5 rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">
          <CmdIcon className="h-3 w-3" />K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1.5">
        <AiStatus />
        <ThemeToggle />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative" data-testid="notifications-btn">
              <Bell className="h-[18px] w-[18px]" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72">
            <DropdownMenuLabel>Notifications</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="px-2 py-6 text-center text-xs text-muted-foreground">
              You're all caught up.
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button data-testid="user-profile" className="ml-1 rounded-full outline-none ring-primary/50 focus-visible:ring-2">
              <Avatar className="h-8 w-8 border border-border">
                <AvatarFallback className="bg-primary/15 text-xs font-semibold text-primary">
                  AF
                </AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <p className="text-sm font-medium">Creator</p>
              <p className="text-xs text-muted-foreground">Local workspace</p>
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
