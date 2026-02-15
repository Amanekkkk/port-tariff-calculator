from pathlib import Path
from app.config import get_gemini_api_key, get_tariff_pdf_path_or_raise
from app.models import TariffResult, VesselInfo
from app.rag import build_vector_store, retrieve_tariff_context, retrieve_tariff_context_multi
from app.tariff_calculator import calculate_tariffs, format_vessel_context


def run_tariff_calculation(
    vessel: VesselInfo,
    port: str,
    force_rebuild_index: bool = False,
    api_key: str | None = None,
    debug: bool = False,
) -> TariffResult:

    pdf_path = get_tariff_pdf_path_or_raise()

    collection = build_vector_store(force_rebuild=force_rebuild_index)

    tariff_context = retrieve_tariff_context_multi(collection, vessel, port)
    if not tariff_context or not tariff_context.strip():
        query = (
            f"Calculate tariffs for vessel at {port}: "
            f"GT {vessel.gt}, NT {vessel.nt}, LOA {vessel.loa}m, "
            f"Beam {vessel.beam}m, days alongside {vessel.days_aside}. "
            "light dues, port dues, towage, VTS, pilotage, running of vessel lines."
        )
        tariff_context = retrieve_tariff_context(collection, query)

    if not tariff_context or not tariff_context.strip():
        from app.pdf_loader import load_pdf_text

        tariff_context = load_pdf_text(pdf_path)[:35000]

    return calculate_tariffs(
        vessel=vessel,
        port=port,
        tariff_context=tariff_context,
        api_key=api_key or get_gemini_api_key(),
        debug=debug,
    )
