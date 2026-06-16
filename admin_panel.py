# admin_panel.py - Standalone Admin / Configuration panel (port 8090).
# Edit SLA + notification recipients. Reads/writes settings.py (JSON-backed).
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import settings as st

app = FastAPI(title="NOC Admin")
ADMIN_PORT = 8090

@app.get("/api/settings")
def api_settings():
    return JSONResponse(st.load_settings())

@app.post("/api/sla")
async def api_sla(req: Request):
    body = await req.json()
    try:
        secs = int(body.get("sla_seconds", 300))
        st.save_settings({"sla_seconds": max(30, secs)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)
    return JSONResponse(st.load_settings())

@app.post("/api/recipient/add")
async def api_add(req: Request):
    b = await req.json()
    st.add_recipient(b.get("team",""), b.get("channel","email"), b.get("contact",""))
    return JSONResponse(st.load_settings())

@app.post("/api/recipient/remove")
async def api_remove(req: Request):
    b = await req.json()
    try:
        st.remove_recipient(int(b.get("index", -1)))
    except Exception:
        pass
    return JSONResponse(st.load_settings())

PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>NOC Admin · Configuration</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Inter,sans-serif;background:#EEF2FB;color:#1E293B;padding:0}
.top{background:linear-gradient(120deg,#6366F1,#8B5CF6,#06B6D4);color:#fff;padding:20px 28px}
.top h1{font-family:'Space Grotesk';font-size:1.4rem}
.top p{color:#E0E7FF;font-size:.85rem;font-family:'JetBrains Mono';margin-top:4px}
.wrap{max-width:880px;margin:22px auto;padding:0 20px;display:grid;gap:18px}
.card{background:#fff;border:1px solid #E2E8F5;border-radius:16px;padding:22px 24px;box-shadow:0 10px 30px rgba(80,100,200,.10)}
.card h2{font-family:'Space Grotesk';font-size:1.05rem;margin-bottom:14px;display:flex;align-items:center;gap:8px}
label{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#64748B;font-weight:700;display:block;margin-bottom:6px}
input,select{font-family:Inter;font-size:.9rem;padding:9px 12px;border:1px solid #D8E0F0;border-radius:9px;width:100%}
.row{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap}
.row>div{flex:1;min-width:140px}
button{font-family:'Space Grotesk';font-weight:700;color:#fff;border:none;border-radius:10px;padding:10px 18px;cursor:pointer;
  background:linear-gradient(120deg,#6366F1,#8B5CF6);box-shadow:0 6px 18px rgba(99,102,241,.35)}
button.del{background:#FEE2E2;color:#DC2626;box-shadow:none;padding:7px 12px;font-size:.8rem}
.slabox{display:flex;align-items:center;gap:14px}
.slabox .cur{font-family:'JetBrains Mono';font-size:1.6rem;font-weight:700;color:#6366F1}
table{width:100%;border-collapse:collapse;margin-top:6px}
th{text-align:left;font-size:.66rem;text-transform:uppercase;letter-spacing:.06em;color:#94A3B8;padding:8px 10px;border-bottom:1px solid #EEF2FB}
td{padding:10px;border-bottom:1px solid #F4F7FD;font-size:.88rem}
.chan{font-family:'JetBrains Mono';font-size:.7rem;font-weight:700;padding:2px 9px;border-radius:6px}
.c-page{background:#FEE2E2;color:#DC2626}.c-email{background:#EEF2FF;color:#4F46E5}.c-slack{background:#D1FAE5;color:#059669}
.ok{color:#059669;font-size:.8rem;font-weight:600;margin-left:10px}
</style></head><body>
<div class=top><h1>&#9881;&#65039; NOC Copilot &middot; Admin Configuration</h1>
<p>Live operational settings &middot; changes apply to new incident simulations</p></div>
<div class=wrap>
  <div class=card>
    <h2>&#9201;&#65039; SLA Timer</h2>
    <div class=slabox>
      <div style="flex:0 0 auto"><label>Current SLA window</label><span class=cur id=slacur>--</span></div>
      <div style="flex:1"><label>Set SLA (seconds)</label><input id=slainp type=number min=30 value=300></div>
      <button onclick=saveSLA()>Save SLA</button><span class=ok id=slaok></span>
    </div>
  </div>
  <div class=card>
    <h2>&#128226; Notification Manager</h2>
    <table><thead><tr><th>Team</th><th>Channel</th><th>Contact</th><th></th></tr></thead>
    <tbody id=recips></tbody></table>
    <div class=row style="margin-top:16px">
      <div><label>Team / Role</label><input id=nteam placeholder="e.g. Field Ops"></div>
      <div><label>Channel</label><select id=nchan><option>email</option><option>slack</option><option>page</option></select></div>
      <div><label>Contact</label><input id=ncontact placeholder="email / #channel"></div>
      <button onclick=addRecip()>Add</button>
    </div>
  </div>
</div>
<script>
async function load(){
  const r=await fetch('api/settings'); const s=await r.json();
  document.getElementById('slacur').textContent=(s.sla_seconds/60).toFixed(1)+' min';
  document.getElementById('slainp').value=s.sla_seconds;
  const tb=document.getElementById('recips');
  tb.innerHTML=(s.notification_recipients||[]).map((x,i)=>`<tr>
    <td><b>${x.team}</b></td>
    <td><span class="chan c-${x.channel}">${x.channel.toUpperCase()}</span></td>
    <td style="font-family:JetBrains Mono;font-size:.82rem">${x.contact}</td>
    <td><button class=del onclick=delRecip(${i})>Remove</button></td></tr>`).join('');
}
async function saveSLA(){
  const v=parseInt(document.getElementById('slainp').value);
  await fetch('api/sla',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sla_seconds:v})});
  document.getElementById('slaok').textContent='✓ saved'; setTimeout(()=>document.getElementById('slaok').textContent='',1500); load();
}
async function addRecip(){
  const team=document.getElementById('nteam').value, channel=document.getElementById('nchan').value, contact=document.getElementById('ncontact').value;
  if(!team)return;
  await fetch('api/recipient/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({team,channel,contact})});
  document.getElementById('nteam').value='';document.getElementById('ncontact').value=''; load();
}
async function delRecip(i){
  await fetch('api/recipient/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:i})}); load();
}
load();
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=ADMIN_PORT)
