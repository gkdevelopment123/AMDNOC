f = "app.py"
s = open(f).read()
# import settings
if "import settings as _settings" not in s:
    s = s.replace("from config import SLA_SECONDS",
                  "from config import SLA_SECONDS\nimport settings as _settings")
# make p_sla read the live SLA value instead of the constant
s = s.replace(
    "    rem = max(0, SLA_SECONDS - elapsed)",
    "    sla = _settings.get_sla_seconds()\n    rem = max(0, sla - elapsed)")
open(f, "w").write(s)
print("Step 3a: dashboard SLA now reads from settings.")
