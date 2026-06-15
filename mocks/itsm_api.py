from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI()

# In-memory storage for tickets
tickets_db = {}

class CreateTicketRequest(BaseModel):
    priority: str
    title: str
    description: str
    affected_devices: Optional[List[str]] = None
    root_cause: Optional[str] = None

class UpdateTicketRequest(BaseModel):
    ticket_id: str
    status: str
    work_note: Optional[str] = None

class TicketResponse(BaseModel):
    ticket_id: str
    status: str
    priority: str
    created_at: str
    url: str

class UpdateTicketResponse(BaseModel):
    ticket_id: str
    status: str
    updated_at: str
    url: str

@app.post("/create_ticket", response_model=TicketResponse)
async def create_ticket(request: CreateTicketRequest):
    # Generate a unique ticket ID
    ticket_id = f"INC{str(uuid.uuid4().int)[:7]}"
    
    # Store ticket in memory
    tickets_db[ticket_id] = {
        "ticket_id": ticket_id,
        "status": "New",
        "priority": request.priority,
        "title": request.title,
        "description": request.description,
        "affected_devices": request.affected_devices or [],
        "root_cause": request.root_cause,
        "created_at": datetime.now().isoformat(),
        "url": f"https://itsm.mock/{ticket_id}"
    }
    
    # Return ticket info
    return TicketResponse(
        ticket_id=ticket_id,
        status="New",
        priority=request.priority,
        created_at=datetime.now().isoformat(),
        url=f"https://itsm.mock/{ticket_id}"
    )

@app.post("/update_ticket", response_model=UpdateTicketResponse)
async def update_ticket(request: UpdateTicketRequest):
    # Check if ticket exists
    if request.ticket_id not in tickets_db:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Update ticket status
    tickets_db[request.ticket_id]["status"] = request.status
    tickets_db[request.ticket_id]["updated_at"] = datetime.now().isoformat()
    
    # Add work note if provided
    if request.work_note:
        tickets_db[request.ticket_id]["work_note"] = request.work_note
    
    # Return updated ticket info
    return UpdateTicketResponse(
        ticket_id=request.ticket_id,
        status=request.status,
        updated_at=datetime.now().isoformat(),
        url=f"https://itsm.mock/{request.ticket_id}"
    )