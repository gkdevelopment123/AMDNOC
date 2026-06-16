# patch_ui_compact.py - makes the dashboard compact & centered (max-width container).
# Run once:  python patch_ui_compact.py
import re

f = "app.py"
s = open(f).read()

# 1) Constrain the whole app to a centered max-width column instead of full-bleed.
s = s.replace(
    ".gradio-container{{background:#EEF2FB !important;max-width:100% !important;padding:0 !important}}",
    ".gradio-container{{background:#EEF2FB !important;max-width:1280px !important;margin:0 auto !important;padding:10px 18px 28px !important}}"
)

# 2) Slightly tighten the root padding.
s = s.replace(
    ".cc-root{{font-family:'Inter',sans-serif;color:#1E293B;padding:4px}}",
    ".cc-root{{font-family:'Inter',sans-serif;color:#1E293B;padding:0;max-width:1280px;margin:0 auto}}"
)

# 3) Make panels a touch tighter so the compact layout breathes well.
s = s.replace(
    ".cc-panel{{background:#FFFFFF;border:1px solid #E2E8F5;border-radius:18px;padding:18px 20px;",
    ".cc-panel{{background:#FFFFFF;border:1px solid #E2E8F5;border-radius:16px;padding:16px 18px;"
)

open(f, "w").write(s)
print("UI patched: centered, max-width 1280px, compact panels.")