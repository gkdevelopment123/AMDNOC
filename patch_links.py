f = "app.py"
s = open(f).read()

# 1) Add an editable PROXY_BASE near the top (after the SLA import line)
if "PROXY_BASE" not in s:
    s = s.replace(
        "import settings as _settings",
        'import settings as _settings\n\n'
        '# === EDIT THIS when your pod session URL changes ===\n'
        'PROXY_BASE = "https://notebooks.amd.com/jupyter-hack-team-3049-260614162200-ee4e0c4e/proxy"\n'
        'ITSM_BOARD_URL = f"{PROXY_BASE}/8080/"\n'
        'ADMIN_URL = f"{PROXY_BASE}/8090/"')

# 2) Add link buttons into the HERO header
s = s.replace(
    "'<p><span class=\"live\"></span>LIVE &#183; Qwen3-Coder on AMD Instinct MI300X &#183; multi-agent &#183; 100% on-prem</p></div>')",
    "'<p><span class=\"live\"></span>LIVE &#183; Qwen3-Coder on AMD Instinct MI300X &#183; multi-agent &#183; 100% on-prem</p>'\n"
    "        f'<div class=\"cc-herolinks\"><a href=\"{ITSM_BOARD_URL}\" target=\"_blank\">&#127915; ITSM Board</a>'\n"
    "        f'<a href=\"{ADMIN_URL}\" target=\"_blank\">&#9881;&#65039; Admin Panel</a></div></div>')")

# 3) Make the ITSM ticket card clickable (wrap the ticket id area in a link)
s = s.replace(
    'return (f\'<div class="cc-panel cc-tick"><div class="cc-h">&#127915; ITSM TICKET</div>\'',
    'return (f\'<div class="cc-panel cc-tick"><div class="cc-h">&#127915; ITSM TICKET '
    '<a class="cc-ticklink" href="{ITSM_BOARD_URL}" target="_blank">open board &#8599;</a></div>\'')

# 4) CSS for the hero links + ticket link
s = s.replace(
    "#cc-hero p{{color:#E0E7FF;margin:6px 0 0;font-size:.85rem;font-family:'JetBrains Mono'}}",
    "#cc-hero p{{color:#E0E7FF;margin:6px 0 0;font-size:.85rem;font-family:'JetBrains Mono'}}\n"
    ".cc-herolinks{{margin-top:12px;display:flex;gap:10px}}\n"
    ".cc-herolinks a{{font-family:'Space Grotesk';font-weight:700;font-size:.8rem;color:#fff;"
    "background:rgba(255,255,255,.18);padding:7px 14px;border-radius:10px;text-decoration:none;"
    "border:1px solid rgba(255,255,255,.25)}}\n"
    ".cc-herolinks a:hover{{background:rgba(255,255,255,.30)}}\n"
    ".cc-ticklink{{margin-left:auto;font-family:'JetBrains Mono';font-size:.62rem;color:#6366F1;text-decoration:none;font-weight:700}}")

open(f, "w").write(s)
print("Step 3c: header links + clickable ticket card added.")
