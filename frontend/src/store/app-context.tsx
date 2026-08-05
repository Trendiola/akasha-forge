import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import type { Project } from "@/types";

interface AppState {
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  commandOpen: boolean;
  setCommandOpen: (v: boolean) => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(
    () => localStorage.getItem("akasha.activeProject")
  );
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(
    () => localStorage.getItem("akasha.sidebarCollapsed") === "true"
  );
  const [commandOpen, setCommandOpen] = useState(false);

  const setActiveProjectId = useCallback((id: string | null) => {
    setActiveProjectIdState(id);
    if (id) localStorage.setItem("akasha.activeProject", id);
    else localStorage.removeItem("akasha.activeProject");
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      localStorage.setItem("akasha.sidebarCollapsed", String(!prev));
      return !prev;
    });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <AppContext.Provider
      value={{
        activeProjectId,
        setActiveProjectId,
        sidebarCollapsed,
        toggleSidebar,
        commandOpen,
        setCommandOpen,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppState => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
};

export type { Project };
