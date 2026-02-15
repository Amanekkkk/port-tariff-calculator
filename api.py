import json
import os
from pathlib import Path
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.models import VesselInfo
from app.service import run_tariff_calculation

sys.path.insert(0, str(Path(__file__).resolve().parent))

app = FastAPI(
    title="Port Tariff Calculator API",
    description="Calculate South African port tariffs for vessels (light dues, port dues, towage, VTS, pilotage, running of vessel lines)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VesselRequest(BaseModel):
    name: str = Field(default="", description="Vessel name")
    vessel_type: str = Field(default="", description="Vessel type (e.g. Bulk Carrier)")
    gt: float = Field(ge=0, description="Gross Tonnage")
    nt: float = Field(ge=0, description="Net Tonnage")
    dwt: float = Field(default=0, ge=0, description="Deadweight Tonnage")
    loa: float = Field(ge=0, description="Length Overall (m)")
    beam: float = Field(ge=0, description="Beam (m)")
    moulded_depth: float = Field(default=0, ge=0, description="Moulded Depth (m)")
    lbp: float = Field(default=0, ge=0, description="Length Between Perpendiculars")
    draft_sw_s: float = Field(default=0, ge=0, description="Draft SW Stern (m)")
    draft_sw_w: float = Field(default=0, ge=0, description="Draft SW Waist (m)")
    draft_sw_t: float = Field(default=0, ge=0, description="Draft SW Bow (m)")
    days_aside: float = Field(default=0, ge=0, description="Days alongside")
    cargo_quantity: float = Field(default=0, ge=0, description="Cargo quantity (MT)")
    number_of_operations: int = Field(default=0, ge=0, description="Number of operations")
    number_of_holds: int = Field(default=0, ge=0, description="Number of holds")
    suez_gt: float | None = Field(default=None, description="Suez Gross Tonnage")
    suez_nt: float | None = Field(default=None, description="Suez Net Tonnage")
    raw_text: str = Field(default="", description="Additional vessel info as text")


class CalculateRequest(BaseModel):
    vessel: VesselRequest
    port: str = Field(
        ...,
        description="Port of call: Durban, Saldanha, or Richard's Bay",
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "port-tariff-calculator"}


@app.post("/calculate")
def calculate(request: CalculateRequest):
    port = request.port.strip()
    if port.lower() == "richards bay":
        port = "Richard's Bay"
    if port not in ("Durban", "Saldanha", "Richard's Bay"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported port: {request.port}. Use Durban, Saldanha, or Richard's Bay.",
        )

    vessel_dict = request.vessel.model_dump()
    vessel = VesselInfo.from_dict(vessel_dict)

    try:
        result = run_tariff_calculation(
            vessel=vessel,
            port=port,
        )
        return result.to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/calculate/raw")
def calculate_raw(body: dict):
    vessel = body.get("vessel", body)
    port = body.get("port", "Durban")
    if isinstance(vessel, dict):
        vessel = VesselInfo.from_dict(vessel)
    else:
        raise HTTPException(status_code=400, detail="vessel must be an object")

    try:
        result = run_tariff_calculation(vessel=vessel, port=port)
        return result.to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _run_server():
    uvicorn.run(
        "api:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8004)),
        reload=True,
    )

if __name__ == "__main__":
    _run_server()
