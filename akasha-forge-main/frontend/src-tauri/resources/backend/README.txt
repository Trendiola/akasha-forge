# Akasha Forge — one-dir PyInstaller backend goes here for a Windows build.
#
# After building on Windows (see backend/BUILD_DESKTOP.md), copy the WHOLE
# one-dir output folder to:
#
#   frontend/src-tauri/resources/backend/AkashaForgeBackend/
#       AkashaForgeBackend.exe
#       _internal/ ...
#
# Tauri bundles it as a read-only resource (tauri.conf.json -> bundle.resources).
# At runtime the shell resolves:
#   <resource_dir>/resources/backend/AkashaForgeBackend/AkashaForgeBackend.exe
#
# This directory is intentionally empty in git (the frozen binary is large and
# platform-specific — never commit it). See .gitignore.
