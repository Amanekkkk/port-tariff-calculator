import argparse
import json
import sys
from pathlib import Path
from app.models import VesselInfo
from app.service import run_tariff_calculation

sys.path.insert(0, str(Path(__file__).resolve().parent))

def load_vessel(path: str) -> VesselInfo:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return VesselInfo.from_dict(data)


def main():
    parser = argparse.ArgumentParser(description="Calculate South African port tariffs")
    parser.add_argument(
        "--vessel",
        default="data/example_vessel.json",
        help="Path to vessel JSON file (default: data/example_vessel.json)",
    )
    parser.add_argument(
        "--port",
        default="Durban",
        choices=["Durban", "Saldanha", "Richard's Bay", "Richards Bay"],
        help="Port of call (default: Durban)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild of vector index from PDF",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print raw LLM response for debugging",
    )
    args = parser.parse_args()

    vessel_path = Path(args.vessel)
    if not vessel_path.exists():
        print(f"Error: Vessel file not found: {vessel_path}", file=sys.stderr)
        sys.exit(1)

    vessel = load_vessel(str(vessel_path))

    # Normalizing port name
    port = args.port
    if port == "Richards Bay":
        port = "Richard's Bay"

    print(f"Calculating tariffs for {vessel.name} at {port}...")
    print("(This may take a moment on first run while building the vector index)\n")

    try:
        result = run_tariff_calculation(
            vessel=vessel,
            port=port,
            force_rebuild_index=args.rebuild,
            debug=args.debug,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output = result.to_dict()

    if args.output == "json":
        print(json.dumps(output, indent=2))
    else:
        print("Tariff Calculation Results (ZAR)")
        print("-" * 45)
        print(f"Light dues:                    {output['light_dues']:>15,.2f}")
        print(f"Port dues:                     {output['port_dues']:>15,.2f}")
        print(f"Towage dues:                   {output['towage_dues']:>15,.2f}")
        print(f"VTS dues:                      {output['vehicle_traffic_services_vts_dues']:>15,.2f}")
        print(f"Pilotage dues:                 {output['pilotage_dues']:>15,.2f}")
        print(f"Running of vessel lines dues:  {output['running_of_vessel_lines_dues']:>15,.2f}")
        print("-" * 45)

        # Ground truth
        if vessel.name.upper() == "SUDESTADA" and port == "Durban":
            ground_truth = {
                "light_dues": 60062.04,
                "port_dues": 199549.22,
                "towage_dues": 147074.38,
                "vehicle_traffic_services_vts_dues": 33315.75,
                "pilotage_dues": 47189.94,
                "running_of_vessel_lines_dues": 19639.50,
            }
            print("\nGround Truth Comparison:")
            for k, v in output.items():
                gt = ground_truth.get(k)
                if gt is not None:
                    diff = v - gt
                    pct = (diff / gt * 100) if gt else 0
                    print(f"  {k}: calculated={v:,.2f}, expected={gt:,.2f}, diff={diff:+,.2f} ({pct:+.1f}%)")


if __name__ == "__main__":
    main()
