f = "itsm_board.py"
s = open(f).read()
def must(s, old, new, label):
    if old not in s:
        raise SystemExit(f"FAILED at {label}")
    return s.replace(old, new, 1)
if "api_resolve" in s:
    raise SystemExit("Already applied.")

anchor = '@app.get("/", response_class=HTMLResponse)'
new_endpoint = '''@app.post("/api/resolve/{tid}")
def api_resolve(tid: str):
    import requests as _rq
    try:
        note = ("Incident resolved from ITSM board. Remediation actions applied; "
                "connectivity restored and alarms cleared.")
        r = _rq.post(f"{ITSM_API_URL}/update_ticket",
                     json={"ticket_id": tid, "status": "Resolved", "work_note": note}, timeout=5)
        return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)


@app.get("/", response_class=HTMLResponse)'''
s = must(s, anchor, new_endpoint, "endpoint")

old_tip = '''    <div class=sec>Work notes &amp; activity</div>${notes}
    <div class=hint>💬 Tip: on the NOC dashboard, tell the Copilot e.g. <b>"resolve ${x.ticket_id} and add a note that BGP was restored"</b> — this record updates automatically.</div>`;'''
new_tip = '''    <div class=sec>Work notes &amp; activity</div>${notes}
    ${(x.status==='Resolved'||x.status==='Closed')
       ? '<div class=resolved-banner>\\u2705 This incident is '+x.status+'.</div>'
       : '<button class=resolvebtn onclick="resolveTicket(\\''+x.ticket_id+'\\')">\\u2705 Resolve this incident</button>'}`;'''
s = must(s, old_tip, new_tip, "tip")

anchor2 = "function closeD(){"
resolve_js = '''async function resolveTicket(id){
  await fetch('api/resolve/'+id,{method:'POST'});
  openD(id);
  load();
}
function closeD(){'''
s = must(s, anchor2, resolve_js, "closeD")

anchor3 = ".hint{margin-top:22px;"
css_add = '''.resolvebtn{margin-top:20px;width:100%;background:linear-gradient(120deg,#10B981,#059669);color:#fff;
  border:none;border-radius:11px;padding:13px;font-family:'Space Grotesk',sans-serif;font-weight:700;
  font-size:.95rem;cursor:pointer;box-shadow:0 8px 22px rgba(16,185,129,.35)}
.resolvebtn:hover{transform:translateY(-1px)}
.resolved-banner{margin-top:20px;background:#E2F6EE;color:#149563;border-radius:11px;padding:13px;
  text-align:center;font-weight:700;font-size:.9rem}
.hint{margin-top:22px;'''
if anchor3 in s:
    s = s.replace(anchor3, css_add, 1)
else:
    s = s.replace("</style>", css_add.replace(".hint{margin-top:22px;","") + "\n</style>", 1)

open(f, "w").write(s)
print("Board patched: per-ticket Resolve button + tip hidden on resolved tickets.")
