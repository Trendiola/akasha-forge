//! AF-DESKTOP-006 — Akasha Forge desktop shell + backend sidecar lifecycle.
//!
//! Lifecycle (see the sprint spec):
//!   resolve AKASHA_DATA_DIR (OS app-data) → pick a free 127.0.0.1 port →
//!   launch the frozen `AkashaForgeBackend` sidecar with the local-mode env →
//!   bounded /api/health handshake → inject `window.__AKASHA_RUNTIME_CONFIG__`
//!   BEFORE the React bundle loads → open the window → terminate the backend
//!   gracefully on exit (no orphans).
//!
//! Reuses the AF-DESKTOP-002 frontend contract (`runtime.ts` reads the injected
//! global; `App.tsx` switches to HashRouter when `desktop === true`). No second
//! URL resolver is introduced.

use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

/// Handle to the single backend child process (guards against duplicates/orphans).
struct BackendProcess(Mutex<Option<Child>>);

/// Bind to port 0 on loopback, let the OS assign a free port, then release it.
fn pick_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .unwrap_or(8001)
}

/// Locate the frozen one-dir backend executable.
///
/// AF-DESKTOP-005 produces a PyInstaller **one-dir** bundle, so the sidecar is a
/// folder (`AkashaForgeBackend/` + `_internal/`) shipped as a Tauri *resource*,
/// not a single-file `externalBin`. We resolve the executable inside it.
fn resolve_backend_binary(app: &tauri::AppHandle) -> Option<PathBuf> {
    let exe = if cfg!(windows) {
        "AkashaForgeBackend.exe"
    } else {
        "AkashaForgeBackend"
    };

    // 1) Explicit override (used by the validation harness / advanced setups).
    if let Ok(p) = std::env::var("AKASHA_BACKEND_BIN") {
        let pb = PathBuf::from(p);
        if pb.exists() {
            return Some(pb);
        }
    }

    // 2) Bundled resource (production install).
    if let Ok(res_dir) = app.path().resource_dir() {
        let p = res_dir
            .join("resources")
            .join("backend")
            .join("AkashaForgeBackend")
            .join(exe);
        if p.exists() {
            return Some(p);
        }
    }

    // 3) Dev fallback: repo-relative frozen build from AF-DESKTOP-005.
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("backend")
        .join("dist")
        .join("AkashaForgeBackend")
        .join(exe);
    if dev.exists() {
        return Some(dev);
    }

    None
}

/// Poll `${url}` until it reports `{"status":"ok"}` or the deadline passes.
/// Bounded — never loops forever.
fn wait_for_health(url: &str, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    let client = match reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
    {
        Ok(c) => c,
        Err(_) => return false,
    };
    while Instant::now() < deadline {
        if let Ok(resp) = client.get(url).send() {
            if resp.status().is_success() {
                if let Ok(j) = resp.json::<serde_json::Value>() {
                    if j.get("status").and_then(|s| s.as_str()) == Some("ok") {
                        return true;
                    }
                }
            }
        }
        std::thread::sleep(Duration::from_millis(600));
    }
    false
}

/// JSON-escape a string for embedding inside the injected init script.
fn js_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

/// Gracefully stop the backend child, falling back to a force-kill. Idempotent.
fn shutdown_backend(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendProcess>() {
        if let Some(mut child) = state.0.lock().unwrap().take() {
            #[cfg(unix)]
            {
                // Ask uvicorn to shut down cleanly (SIGINT), then wait briefly.
                unsafe {
                    libc::kill(child.id() as i32, libc::SIGINT);
                }
                let deadline = Instant::now() + Duration::from_millis(4000);
                while Instant::now() < deadline {
                    match child.try_wait() {
                        Ok(Some(_)) => return,
                        _ => std::thread::sleep(Duration::from_millis(150)),
                    }
                }
            }
            // Fallback / Windows path: TerminateProcess.
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

pub fn run() {
    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let handle = app.handle().clone();

            // 1) OS application-data directory (never Program Files / resource dir).
            let data_dir = handle
                .path()
                .app_data_dir()
                .expect("could not resolve app data dir");
            std::fs::create_dir_all(&data_dir).ok();

            // 2) Free loopback port (avoids clashing with a dev backend on 8001).
            let port = pick_free_port();
            let backend_url = format!("http://127.0.0.1:{}", port);

            // 3) Launch the frozen backend sidecar with the local desktop env.
            //    The backend self-provisions its master key via the AF-DESKTOP-007
            //    secure vault (OS keyring/DPAPI on Windows) — the shell passes NO
            //    secrets: no AKASHA_SECRET_KEY, no provider keys, nothing sensitive
            //    on the command line or in the injected runtime config.
            //    AKASHA_SKIP_SIDECAR=1 lets `tauri dev` reuse an already-running
            //    backend (dev only) via AKASHA_DEV_BACKEND_URL.
            let skip = std::env::var("AKASHA_SKIP_SIDECAR")
                .map(|v| v == "1")
                .unwrap_or(false);

            if !skip {
                match resolve_backend_binary(&handle) {
                    Some(bin) => {
                        let mut cmd = Command::new(&bin);
                        cmd.env("AKASHA_HOST", "127.0.0.1")
                            .env("AKASHA_PORT", port.to_string())
                            .env("AKASHA_DATA_DIR", &data_dir)
                            .env("STORAGE_BACKEND", "local")
                            .env("AKASHA_DB_BACKEND", "local")
                            .env("DB_NAME", "akasha_forge");
                        #[cfg(windows)]
                        {
                            use std::os::windows::process::CommandExt;
                            // CREATE_NO_WINDOW — no console flashes behind the app.
                            cmd.creation_flags(0x0800_0000);
                        }
                        match cmd.spawn() {
                            Ok(child) => {
                                *app.state::<BackendProcess>().0.lock().unwrap() = Some(child);
                            }
                            Err(e) => eprintln!("[akasha] failed to spawn backend: {e}"),
                        }
                    }
                    None => eprintln!(
                        "[akasha] AkashaForgeBackend not found (bundle it as a resource or set AKASHA_BACKEND_BIN)"
                    ),
                }
            }

            // 5) Bounded health handshake — the app only becomes usable once ready.
            let effective_url = if skip {
                std::env::var("AKASHA_DEV_BACKEND_URL").unwrap_or_else(|_| backend_url.clone())
            } else {
                backend_url.clone()
            };
            let ready = if skip {
                true
            } else {
                wait_for_health(&format!("{}/api/health", effective_url), Duration::from_secs(30))
            };

            // 6) Inject the runtime config BEFORE any page script runs, then open
            //    the window. `initialization_script` guarantees ordering (unlike a
            //    post-load eval), satisfying the AF-DESKTOP-002 contract.
            let data_dir_js = js_escape(&data_dir.to_string_lossy());
            let init = if ready {
                format!(
                    "window.__AKASHA_RUNTIME_CONFIG__={{desktop:true,backendUrl:\"{}\",appDataDir:\"{}\"}};",
                    effective_url, data_dir_js
                )
            } else {
                format!(
                    "window.__AKASHA_RUNTIME_CONFIG__={{desktop:true,backendUrl:\"{}\",appDataDir:\"{}\",startupError:\"Akasha Forge could not start its engine. Please restart the application.\"}};",
                    effective_url, data_dir_js
                )
            };

            WebviewWindowBuilder::new(&handle, "main", WebviewUrl::App("index.html".into()))
                .title("Akasha Forge")
                .inner_size(1440.0, 900.0)
                .min_inner_size(1024.0, 700.0)
                .initialization_script(&init)
                .build()?;

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Akasha Forge")
        .run(|app_handle, event| match event {
            // Terminate the backend when the app is closing — no orphans.
            RunEvent::ExitRequested { .. } | RunEvent::Exit => {
                shutdown_backend(app_handle);
            }
            _ => {}
        });
}
