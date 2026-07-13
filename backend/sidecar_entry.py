"""PyInstaller entry point for the v2.1 Tauri analysis sidecar."""
import sys

# A frozen Windows console can otherwise inherit the active OEM code page even
# when the parent sets PYTHONUTF8. The Rust host requires strict UTF-8 JSON.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.bridge import main


if __name__ == "__main__":
    raise SystemExit(main())
