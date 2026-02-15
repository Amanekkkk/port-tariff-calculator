from dataclasses import dataclass
from typing import Optional


@dataclass
class VesselInfo:
    name: str = ""
    vessel_type: str = ""
    gt: float = 0.0
    nt: float = 0.0
    dwt: float = 0.0
    loa: float = 0.0
    beam: float = 0.0
    moulded_depth: float = 0.0
    lbp: float = 0.0
    draft_sw_s: float = 0.0
    draft_sw_w: float = 0.0
    draft_sw_t: float = 0.0
    days_aside: float = 0.0
    cargo_quantity: float = 0.0
    number_of_operations: int = 0
    number_of_holds: int = 0
    suez_gt: Optional[float] = None
    suez_nt: Optional[float] = None
    raw_text: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "VesselInfo":
        def parse_num(val) -> float:
            if val is None or val == "" or val == "[Not provided]":
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).replace(",", "").strip()
            return float(s) if s and s != "-" else 0.0

        return cls(
            name=str(data.get("name", data.get("vessel_name", ""))),
            vessel_type=str(data.get("vessel_type", data.get("type", ""))),
            gt=parse_num(data.get("gt", data.get("gross_tonnage", 0))),
            nt=parse_num(data.get("nt", data.get("net_tonnage", 0))),
            dwt=parse_num(data.get("dwt", 0)),
            loa=parse_num(data.get("loa", 0)),
            beam=parse_num(data.get("beam", 0)),
            moulded_depth=parse_num(data.get("moulded_depth", 0)),
            lbp=parse_num(data.get("lbp", 0)),
            draft_sw_s=parse_num(data.get("draft_sw_s", 0)),
            draft_sw_w=parse_num(data.get("draft_sw_w", 0)),
            draft_sw_t=parse_num(data.get("draft_sw_t", 0)),
            days_aside=parse_num(data.get("days_aside", data.get("days_alongside", 0))),
            cargo_quantity=parse_num(data.get("cargo_quantity", 0)),
            number_of_operations=int(data.get("number_of_operations", 0) or 0),
            number_of_holds=int(data.get("number_of_holds", 0) or 0),
            suez_gt=parse_num(data.get("suez_gt")) if data.get("suez_gt") else None,
            suez_nt=parse_num(data.get("suez_nt")) if data.get("suez_nt") else None,
            raw_text=str(data.get("raw_text", "")),
        )

@dataclass
class TariffResult:

    light_dues: float
    port_dues: float
    towage_dues: float
    vts_dues: float
    pilotage_dues: float
    running_of_vessel_lines_dues: float
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "light_dues": round(self.light_dues, 2),
            "port_dues": round(self.port_dues, 2),
            "towage_dues": round(self.towage_dues, 2),
            "vehicle_traffic_services_vts_dues": round(self.vts_dues, 2),
            "pilotage_dues": round(self.pilotage_dues, 2),
            "running_of_vessel_lines_dues": round(self.running_of_vessel_lines_dues, 2),
        }
