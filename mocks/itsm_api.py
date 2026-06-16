# mocks/itsm_api.py - ServiceNow-style mock ITSM API (upgraded)
# Keeps the original create_ticket / update_ticket contract used by pipeline.py,
# and ADDS board endpoints (list, get, work-notes history, flexible update).

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

app = FastAPI(title="Mock ITSM (ServiceNow-style)")

# In-memory ticket store
tickets_db: Dict[str, Dict[str, Any]] = {}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- request models ----------
class CreateTicketRequest(BaseModel):
    priority: str
    title: str
    description: str
    affected_devices: Optional[List[str]] = None
    root_cause: Optional[str] = None


class UpdateTicketRequest(BaseModel):
    ticket_id: str
    status: Optional[str] = None
    work_note: Optional[str] = None
    # full control: any of these may be set from chat
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    assignment_group: Optional[str] = None
    category: Optional[str] = None


# ---------- create ----------
@app.post("/create_ticket")
async def create_ticket(req: CreateTicketRequest):
    ticket_id = f"INC{str(uuid.uuid4().int)[:7]}"
    now = _now()
    tickets_db[ticket_id] = {
        "ticket_id": ticket_id,
        "number": ticket_id,
        "status": "New",
        "priority": req.priority,
        "title": req.title,
        "short_description": req.title,
        "description": req.description,
        "affected_devices": req.affected_devices or [],
        "root_cause": req.root_cause,
        "assigned_to": "— unassigned —",
        "assignment_group": "Network Operations",
        "category": "Network",
        "created_at": now,
        "updated_at": now,
        "url": f"https://itsm.mock/{ticket_id}",
        "work_notes": [
            {"ts": now, "author": "NOC Copilot", "text": "Incident auto-created by NOC Agentic Copilot."}
        ],
    }
    return tickets_db[ticket_id]


# ---------- flexible update (full control) ----------
@app.post("/update_ticket")
async def update_ticket(req: UpdateTicketRequest):
    if req.ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    t = tickets_db[req.ticket_id]
    changed = []
    for field in ["status", "priority", "assigned_to", "assignment_group", "category"]:
        val = getattr(req, field)
        if val:
            t[field] = val
            changed.append(f"{field} → {val}")
    if req.work_note:
        t["work_notes"].append({"ts": _now(), "author": "NOC Copilot", "text": req.work_note})
        changed.append("work note added")
    t["updated_at"] = _now()
    if changed:
        t["work_notes"].append({"ts": _now(), "author": "system", "text": "Updated: " + "; ".join(changed)})
    return t


# ---------- board endpoints ----------
@app.get("/tickets")
async def list_tickets():
    # newest first
    return sorted(tickets_db.values(), key=lambda x: x["created_at"], reverse=True)


@app.get("/ticket/{ticket_id}")
async def get_ticket(ticket_id: str):
    if ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return tickets_db[ticket_id]


@app.get("/health")
async def health():
    return {"status": "ok", "tickets": len(tickets_db)}