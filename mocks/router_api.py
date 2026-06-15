from fastapi import FastAPI, HTTPException
import time
import random
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class ClearBGPRequest(BaseModel):
    device_id: str
    peer: str

class RestartInterfaceRequest(BaseModel):
    device_id: str
    interface: str

class ResetRouterRequest(BaseModel):
    device_id: str

class ClearBGPResponse(BaseModel):
    status: str
    device_id: str
    action: str
    device_response: str
    latency_ms: int

class RestartInterfaceResponse(BaseModel):
    status: str
    device_id: str
    action: str
    device_response: str
    latency_ms: int

class ResetRouterResponse(BaseModel):
    status: str
    device_id: str
    action: str
    device_response: str
    latency_ms: int

@app.post("/clear_bgp", response_model=ClearBGPResponse)
async def clear_bgp(request: ClearBGPRequest):
    # Simulate ~0.5s latency
    time.sleep(0.5)
    
    # Return realistic response
    return ClearBGPResponse(
        status="SUCCESS",
        device_id=request.device_id,
        action="clear_bgp",
        device_response="BGP session reset, neighbor re-established",
        latency_ms=480
    )

@app.post("/restart_interface", response_model=RestartInterfaceResponse)
async def restart_interface(request: RestartInterfaceRequest):
    # Simulate ~0.5s latency
    time.sleep(0.5)
    
    # Occasionally fail (simulate 20% failure rate)
    if random.random() < 0.2:
        raise HTTPException(status_code=500, detail="Interface restart failed due to device unresponsiveness")
    
    # Return realistic response
    return RestartInterfaceResponse(
        status="SUCCESS",
        device_id=request.device_id,
        action="restart_interface",
        device_response=f"Interface {request.interface} bounced successfully",
        latency_ms=510
    )

@app.post("/reset_router", response_model=ResetRouterResponse)
async def reset_router(request: ResetRouterRequest):
    # Simulate ~0.5s latency
    time.sleep(0.5)
    
    # Return realistic response
    return ResetRouterResponse(
        status="SUCCESS",
        device_id=request.device_id,
        action="reset_router",
        device_response="Router reboot initiated",
        latency_ms=490
    )