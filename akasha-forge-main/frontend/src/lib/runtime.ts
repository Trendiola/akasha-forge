/**
 * Desktop runtime foundation (AF-DESKTOP-002).
 *
 * A future Tauri shell injects `window.__AKASHA_RUNTIME_CONFIG__` before the
 * app loads to declare desktop mode + the dynamically chosen local backend URL.
 * In the web preview this global is absent and we fall back to the build-time
 * env var, then to a safe localhost default. No secrets belong in this object.
 */
export interface AkashaRuntimeConfig {
  desktop?: boolean;
  backendUrl?: string;
  appDataDir?: string;
  startupError?: string;
}

export function getRuntimeConfig(): AkashaRuntimeConfig {
  if (typeof window === "undefined") return {};
  return ((window as unknown as { __AKASHA_RUNTIME_CONFIG__?: AkashaRuntimeConfig }).__AKASHA_RUNTIME_CONFIG__) || {};
}

export function isDesktop(): boolean {
  return getRuntimeConfig().desktop === true;
}

/** Resolve the backend base URL: runtime-injected desktop URL → env var → localhost fallback. */
export function resolveBackendUrl(): string {
  const cfg = getRuntimeConfig();
  const chosen = cfg.backendUrl || process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8001";
  return String(chosen).replace(/\/+$/, "");
}

export interface WaitForBackendOptions {
  timeoutMs?: number;
  intervalMs?: number;
}

/**
 * Poll `${apiBase}/health` until the backend reports ready, then resolve.
 * Bounded by `timeoutMs` (no infinite retry). Throws a friendly error on timeout.
 */
export async function waitForBackend(apiBase: string, opts: WaitForBackendOptions = {}): Promise<boolean> {
  const timeoutMs = opts.timeoutMs ?? 15000;
  const intervalMs = opts.intervalMs ?? 750;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${apiBase}/health`, { method: "GET" });
      if (res.ok) {
        const data = await res.json().catch(() => null);
        if (data && data.status === "ok") return true;
      }
    } catch {
      // backend not up yet — retry until the deadline
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Akasha Forge could not reach its engine in time. Please restart the application and try again.");
}
