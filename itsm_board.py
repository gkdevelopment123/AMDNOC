# itsm_board.py - Standalone ServiceNow-style ITSM board.
# Serves a single self-refreshing HTML page on its own port (8080) that reads
# live tickets from the mock ITSM API (:8002). Click a row -> detail drawer.
# Chat-driven updates on the main dashboard show up here automatically (polling).

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import requests

from config import ITSM_API_URL

app = FastAPI(title="ITSM Board")

ITSM_BOARD_PORT = 8080


@app.get("/api/tickets")
def api_tickets():
    try:
        r = requests.get(f"{ITSM_API_URL}/tickets", timeout=4)
        return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse([], status_code=200)


@app.get("/api/ticket/{tid}")
def api_ticket(tid: str):
    try:
        r = requests.get(f"{ITSM_API_URL}/ticket/{tid}", timeout=4)
        return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ServiceDesk · Incident Management</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#F0F3F9;color:#1B2A4A}
.top{background:#0B1F4D;color:#fff;padding:0 22px;height:54px;display:flex;align-items:center;gap:14px}
.top .logo{display:flex;align-items:center;gap:9px;font-weight:700;font-size:1.05rem}
.top .logo .o{width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,#21C8A6,#1B95E0);display:grid;place-items:center;font-size:.9rem}
.top .nav{display:flex;gap:4px;margin-left:18px}
.top .nav a{color:#AEC2E8;font-size:.84rem;padding:6px 12px;border-radius:7px;text-decoration:none}
.top .nav a.on{background:#16306B;color:#fff}
.top .right{margin-left:auto;display:flex;align-items:center;gap:14px;font-size:.82rem;color:#AEC2E8}
.top .pulse{width:8px;height:8px;border-radius:50%;background:#21C8A6;box-shadow:0 0 8px #21C8A6;animation:p 1.6s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
.wrap{padding:20px 22px}
.crumb{font-size:.8rem;color:#6B7B9E;margin-bottom:14px}
.crumb b{color:#1B2A4A}
.barbox{background:#fff;border:1px solid #DCE3EF;border-radius:12px;box-shadow:0 6px 20px rgba(30,60,120,.07);overflow:hidden}
.barhead{display:flex;align-items:center;padding:13px 18px;border-bottom:1px solid #EAEFF7}
.barhead h2{font-size:1rem;font-weight:700}
.barhead .count{margin-left:10px;background:#E8F0FF;color:#1B6FE0;font-size:.72rem;font-weight:700;padding:2px 9px;border-radius:99px}
.barhead .refresh{margin-left:auto;font-size:.74rem;color:#6B7B9E;font-family:'JetBrains Mono'}
table{width:100%;border-collapse:collapse}
thead th{text-align:left;font-size:.68rem;letter-spacing:.07em;text-transform:uppercase;color:#8493B3;
  padding:11px 18px;border-bottom:1px solid #EAEFF7;font-weight:700;background:#FAFBFE}
tbody td{padding:13px 18px;border-bottom:1px solid #F1F4FA;font-size:.86rem}
tbody tr{cursor:pointer;transition:background .12s}
tbody tr:hover{background:#F5F9FF}
.num{font-family:'JetBrains Mono';font-weight:600;color:#1B6FE0}
.pri{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:.8rem}
.pri .pb{width:4px;height:16px;border-radius:2px}
.state{font-size:.72rem;font-weight:700;padding:3px 11px;border-radius:99px;display:inline-block}
.s-New{background:#FEE9EC;color:#D5304B}.s-InProgress{background:#FFF3DF;color:#B5760B}
.s-Resolved{background:#E2F6EE;color:#149563}.s-Closed{background:#EAEFF7;color:#5B6B8C}
.empty{padding:50px;text-align:center;color:#8493B3;font-style:italic}
/* drawer */
.scrim{position:fixed;inset:0;background:rgba(11,31,77,.35);display:none;z-index:40}
.scrim.on{display:block}
.drawer{position:fixed;top:0;right:-560px;width:540px;max-width:94vw;height:100%;background:#fff;
  box-shadow:-12px 0 40px rgba(11,31,77,.22);z-index:50;transition:right .28s ease;overflow-y:auto}
.drawer.on{right:0}
.dhead{background:linear-gradient(120deg,#0B1F4D,#16306B);color:#fff;padding:20px 24px}
.dhead .dn{font-family:'JetBrains Mono';font-size:1.4rem;font-weight:700}
.dhead .dt{color:#C4D4F2;font-size:.9rem;margin-top:4px}
.dhead .x{position:absolute;top:18px;right:20px;color:#C4D4F2;font-size:1.5rem;cursor:pointer;border:none;background:none}
.dbody{padding:22px 24px}
.frow{display:flex;gap:14px;margin-bottom:16px}
.fld{flex:1}
.fld label{display:block;font-size:.66rem;letter-spacing:.06em;text-transform:uppercase;color:#8493B3;font-weight:700;margin-bottom:4px}
.fld .v{font-size:.9rem;color:#1B2A4A;font-weight:500}
.sec{font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:#1B6FE0;font-weight:700;
  margin:20px 0 10px;padding-bottom:6px;border-bottom:2px solid #EAEFF7}
.desc{background:#F7F9FD;border:1px solid #EAEFF7;border-radius:9px;padding:12px 14px;font-size:.88rem;line-height:1.5;color:#33425E}
.ci{display:inline-block;font-family:'JetBrains Mono';font-size:.74rem;background:#EEF3FB;color:#2A4A86;
  padding:3px 9px;border-radius:6px;margin:2px 4px 2px 0}
.note{padding:11px 0;border-bottom:1px solid #F1F4FA}
.note .meta{font-size:.72rem;color:#8493B3;font-family:'JetBrains Mono';margin-bottom:3px}
.note .meta b{color:#1B6FE0}
.note .txt{font-size:.86rem;color:#33425E}
.resolvebtn{margin-top:20px;width:100%;background:linear-gradient(120deg,#10B981,#059669);color:#fff;
  border:none;border-radius:11px;padding:13px;font-family:'Space Grotesk',sans-serif;font-weight:700;
  font-size:.95rem;cursor:pointer;box-shadow:0 8px 22px rgba(16,185,129,.35)}
.resolvebtn:hover{transform:translateY(-1px)}
.resolved-banner{margin-top:20px;background:#E2F6EE;color:#149563;border-radius:11px;padding:13px;
  text-align:center;font-weight:700;font-size:.9rem}
.hint{margin-top:22px;background:#EEF6FF;border-left:4px solid #1B6FE0;border-radius:0 9px 9px 0;padding:12px 15px;font-size:.82rem;color:#2A4A86}
</style></head><body>
<div class="top">
  <div class="logo"><span class="o">SD</span> ServiceDesk</div>
  <div class="nav"><a class="on" href="#">Incidents</a><a href="#">Problems</a><a href="#">Changes</a><a href="#">CMDB</a></div>
  <div class="right"><span class="pulse"></span>Live · auto-refresh 3s</div>
</div>
<div class="wrap">
  <div class="crumb">Incident Management &nbsp;›&nbsp; <b>All Open Incidents</b></div>
  <div class="barbox">
    <div class="barhead"><h2>Incidents</h2><span class="count" id="cnt">0</span>
      <span class="refresh" id="rf">updated —</span></div>
    <table><thead><tr>
      <th>Number</th><th>Priority</th><th>Short description</th><th>State</th><th>Assignment group</th><th>Updated</th>
    </tr></thead><tbody id="rows"><tr><td colspan="6" class="empty">No incidents yet. Trigger an outage on the NOC dashboard.</td></tr></tbody></table>
  </div>
</div>

<div class="scrim" id="scrim" onclick="closeD()"></div>
<div class="drawer" id="drawer">
  <div class="dhead" style="position:relative">
    <button class="x" onclick="closeD()">×</button>
    <div class="dn" id="d_num"></div><div class="dt" id="d_title"></div>
  </div>
  <div class="dbody" id="d_body"></div>
</div>

<script>
const PRI={ "P1":"#D5304B","P2":"#E8820B","P3":"#1B95E0","P4":"#5B6B8C" };
function stateClass(s){return 's-'+(s||'New').replace(/\\s+/g,'');}
async function load(){
  try{
    const r=await fetch('api/tickets'); const t=await r.json();
    document.getElementById('cnt').textContent=t.length;
    document.getElementById('rf').textContent='updated '+new Date().toLocaleTimeString();
    const tb=document.getElementById('rows');
    if(!t.length){tb.innerHTML='<tr><td colspan=6 class=empty>No incidents yet. Trigger an outage on the NOC dashboard.</td></tr>';return;}
    tb.innerHTML=t.map(x=>`<tr onclick="openD('${x.ticket_id}')">
      <td class=num>${x.number||x.ticket_id}</td>
      <td><span class=pri><span class=pb style="background:${PRI[x.priority]||'#888'}"></span>${x.priority||''}</span></td>
      <td>${x.short_description||x.title||''}</td>
      <td><span class="state ${stateClass(x.status)}">${x.status||'New'}</span></td>
      <td>${x.assignment_group||''}</td>
      <td style="color:#6B7B9E;font-family:JetBrains Mono;font-size:.78rem">${(x.updated_at||'').slice(11)||(x.updated_at||'')}</td>
    </tr>`).join('');
  }catch(e){}
}
async function openD(id){
  const r=await fetch('api/ticket/'+id); const x=await r.json();
  document.getElementById('d_num').textContent=x.number||x.ticket_id;
  document.getElementById('d_title').textContent=x.short_description||x.title||'';
  const cis=(x.affected_devices||[]).map(d=>`<span class=ci>${d}</span>`).join('')||'<span style="color:#8493B3">none</span>';
  const notes=(x.work_notes||[]).slice().reverse().map(n=>`<div class=note><div class=meta><b>${n.author}</b> · ${n.ts}</div><div class=txt>${n.text}</div></div>`).join('')||'<span style="color:#8493B3">No work notes.</span>';
  document.getElementById('d_body').innerHTML=`
    <div class=frow>
      <div class=fld><label>State</label><div class=v><span class="state ${stateClass(x.status)}">${x.status||'New'}</span></div></div>
      <div class=fld><label>Priority</label><div class=v>${x.priority||''}</div></div>
      <div class=fld><label>Category</label><div class=v>${x.category||'Network'}</div></div>
    </div>
    <div class=frow>
      <div class=fld><label>Assigned to</label><div class=v>${x.assigned_to||'— unassigned —'}</div></div>
      <div class=fld><label>Assignment group</label><div class=v>${x.assignment_group||''}</div></div>
    </div>
    <div class=sec>Description</div><div class=desc>${x.description||''}</div>
    <div class=sec>Root cause</div><div class=desc>${x.root_cause||'Pending analysis'}</div>
    <div class=sec>Affected CIs</div><div>${cis}</div>
    <div class=sec>Work notes &amp; activity</div>${notes}
    ${(x.status==='Resolved'||x.status==='Closed')
       ? '<div class=resolved-banner>&#10004; This incident is '+x.status+'</div>'
       : '<button class=resolvebtn id=rbtn>&#10004; Resolve this incident</button>'}`;
  var _rb=document.getElementById('rbtn');
  if(_rb){_rb.onclick=function(){resolveTicket(x.ticket_id);};}
  document.getElementById('scrim').classList.add('on');
  document.getElementById('drawer').classList.add('on');
}
async function resolveTicket(id){
  await fetch('api/resolve/'+id,{method:'POST'});
  openD(id);
  load();
}
function closeD(){document.getElementById('scrim').classList.remove('on');document.getElementById('drawer').classList.remove('on');}
load(); setInterval(load,3000);
</script></body></html>"""


@app.post("/api/resolve/{tid}")
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


@app.get("/", response_class=HTMLResponse)
def board():
    return PAGE


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=ITSM_BOARD_PORT)