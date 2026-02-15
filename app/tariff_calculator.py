import json
import re
import google.generativeai as genai
from app.config import TARIFF_TYPES, get_gemini_api_key, get_gemini_model
from app.models import TariffResult, VesselInfo


def format_vessel_context(vessel: VesselInfo, port: str) -> str:
    """Vessel info for the LLM."""
    parts = [
        f"Port: {port}",
        f"Vessel Name: {vessel.name}",
        f"Vessel Type: {vessel.vessel_type}",
        f"Gross Tonnage (GT): {vessel.gt:,.0f}",
        f"Net Tonnage (NT): {vessel.nt:,.0f}",
        f"DWT: {vessel.dwt:,.0f}",
        f"LOA (m): {vessel.loa}",
        f"Beam (m): {vessel.beam}",
        f"LBP: {vessel.lbp}",
        f"Moulded Depth (m): {vessel.moulded_depth}",
        f"Draft SW S/W/T (m): {vessel.draft_sw_s}/{vessel.draft_sw_w}/{vessel.draft_sw_t}",
        f"Days alongside: {vessel.days_aside}",
        f"Cargo Quantity (MT): {vessel.cargo_quantity:,.0f}",
        f"Number of Operations: {vessel.number_of_operations}",
        f"Number of Holds: {vessel.number_of_holds}",
    ]
    if vessel.suez_gt:
        parts.append(f"Suez GT: {vessel.suez_gt:,.0f}")
    if vessel.suez_nt:
        parts.append(f"Suez NT: {vessel.suez_nt:,.0f}")
    if vessel.raw_text:
        parts.append(f"\nAdditional vessel info:\n{vessel.raw_text}")
    return "\n".join(parts)


def build_calculation_prompt(
    vessel_context: str,
    tariff_context: str,
) -> str:
    return f"""You are an expert in South African port tariff calculations. Use the tariff document excerpts below to calculate the EXACT tariffs payable for the given vessel at the specified port.

## Tariff Document Excerpts
{tariff_context}

## Vessel Parameters and Port
{vessel_context}

## CRITICAL Instructions
1. You MUST calculate and return a numeric ZAR value for EVERY one of the 6 tariffs. Do NOT return null, N/A, 0, or omit any tariff.
2. Each tariff (light dues, port dues, towage, VTS, pilotage, running of vessel lines) has its own rules in the document. Find and apply the correct formula for each.
3. Use GT (gross tonnage), NT (net tonnage), LOA, beam, draft, days alongside as required by each tariff's rules.
4. Apply rates and formulas exactly as specified in the document for the specified port.
5. Return ONLY a valid JSON object with these exact keys (all must have numeric values):
   - light_dues
   - port_dues
   - towage_dues
   - vts_dues
   - pilotage_dues
   - running_of_vessel_lines_dues

Reference (for SUDESTADA at Durban): light_dues ~60062, port_dues ~199549, towage ~147074, vts_dues ~33316, pilotage ~47190, running_of_vessel_lines_dues ~19640. Your calculations should be in a similar magnitude.

Return ONLY the JSON object, no other text."""


def parse_tariff_response(response_text: str) -> TariffResult:
    text = response_text.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    json_match = re.search(r"\{[\s\S]*?\}", text)
    if json_match:
        text = json_match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        numbers = re.findall(r"[\d,]+\.?\d*", text)
        nums = [float(n.replace(",", "")) for n in numbers if n]
        if len(nums) >= 6:
            data = {
                "light_dues": nums[0],
                "port_dues": nums[1],
                "towage_dues": nums[2],
                "vts_dues": nums[3],
                "pilotage_dues": nums[4],
                "running_of_vessel_lines_dues": nums[5],
            }
        else:
            raise ValueError(f"Could not parse tariff response: {response_text[:500]}")

    def get_val(key: str) -> float:
        val = data.get(key)
        if val is None:
            alt = {
                "vts_dues": "vehicle_traffic_services_vts_dues",
                "running_of_vessel_lines_dues": "running_of_vessel_lines_dues",
            }
            val = data.get(alt.get(key, key))
        if isinstance(val, str):
            val = float(val.replace(",", "").replace("ZAR", "").strip())
        return float(val) if val is not None else 0.0

    return TariffResult(
        light_dues=get_val("light_dues"),
        port_dues=get_val("port_dues"),
        towage_dues=get_val("towage_dues"),
        vts_dues=get_val("vts_dues"),
        pilotage_dues=get_val("pilotage_dues"),
        running_of_vessel_lines_dues=get_val("running_of_vessel_lines_dues"),
        raw_response=response_text,
    )


def calculate_tariffs(
    vessel: VesselInfo,
    port: str,
    tariff_context: str,
    api_key: str | None = None,
    debug: bool = False,
) -> TariffResult:
    api_key = api_key or get_gemini_api_key()

    genai.configure(api_key=api_key)
    model_name = get_gemini_model()
    model = genai.GenerativeModel(model_name)

    vessel_context = format_vessel_context(vessel, port)
    prompt = build_calculation_prompt(vessel_context, tariff_context)

    # JSON mode for structured output
    gen_config = genai.types.GenerationConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "light_dues": {"type": "number"},
                "port_dues": {"type": "number"},
                "towage_dues": {"type": "number"},
                "vts_dues": {"type": "number"},
                "pilotage_dues": {"type": "number"},
                "running_of_vessel_lines_dues": {"type": "number"},
            },
            "required": [
                "light_dues", "port_dues", "towage_dues",
                "vts_dues", "pilotage_dues", "running_of_vessel_lines_dues",
            ],
        },
    )

    try:
        response = model.generate_content(prompt, generation_config=gen_config)
    except Exception:
        response = model.generate_content(prompt)
    response_text = response.text if response.text else ""

    if debug:
        print("[DEBUG] Raw LLM response:\n", response_text, "\n")

    return parse_tariff_response(response_text)
