import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";

export function AppShell() {
  return (
    <div
      className="akasha-shell flex h-screen w-screen overflow-hidden text-foreground"
      data-testid="app-shell"
    >
      <Sidebar />

      <div className="relative flex min-w-0 flex-1 flex-col">
        <TopBar />

        <main
          className="grain relative flex-1 overflow-y-auto"
          data-testid="module-outlet"
        >
          <div className="module-enter mx-auto w-full max-w-[1600px] px-8 py-8">
            <Outlet />
          </div>
        </main>
      </div>

      <CommandPalette />
    </div>
  );
}