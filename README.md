# Port Tariff Calculator – Pipeline Documentation

This document describes the end-to-end pipeline used to calculate South African port tariffs from vessel parameters and a tariff PDF document.

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [Pipeline Stages](#2-pipeline-stages)
3. [Data Flow](#3-data-flow)
4. [Module Reference](#4-module-reference)
5. [Configuration](#5-configuration)

---

## 1. Pipeline Overview

The solution uses a **RAG (Retrieval-Augmented Generation)** pipeline that:

1. **Loads** the port tariff PDF and converts it to text (Docling)
2. **Chunks** the text into overlapping segments (pdf_loader)
3. **Embeds** chunks and stores them in a vector database (ChromaDB + Sentence Transformers)
4. **Retrieves** relevant tariff rules for each query (multi-query RAG)
5. **Generates** tariff calculations using an LLM with the retrieved context (Gemini)
6. **Parses** the LLM response and returns structured tariff values

**Input:** Vessel parameters (GT, NT, LOA, beam, draft, days alongside, etc.) + Port name  
**Output:** Six tariff values in ZAR (light dues, port dues, towage, VTS, pilotage, running of vessel lines)

---

## 2. Pipeline Stages

### Stage 1: Document Loading

| Component | `app/pdf_loader.py` → `load_pdf_text()` |
|-----------|----------------------------------------|
| **Input** | Path to PDF (`data/port tariff.pdf`) |
| **Technology** | Docling `DocumentConverter` |
| **Process** | Converts PDF to DoclingDocument, exports as Markdown (or text) |
| **Output** | Full document text with tables and structure preserved |
| **Why** | Layout-aware extraction; tables intact for tariff rules |

---

### Stage 2: Chunking

| Component | `app/pdf_loader.py` → `chunk_text()` |
|-----------|-------------------------------------|
| **Input** | Full document text |
| **Parameters** | `chunk_size=1500`, `overlap=200` |
| **Process** | Splits text into overlapping segments; breaks at newlines when possible |
| **Output** | `list[tuple[str, int]]` — (chunk_text, start_position) |
| **Why** | Chunks fit embedding model limits; overlap keeps context across boundaries |

---

### Stage 3: Embedding & Indexing

| Component | `app/rag.py` → `build_vector_store()` |
|-----------|--------------------------------------|
| **Input** | Chunked documents |
| **Technology** | ChromaDB (persistent), Sentence Transformers `all-MiniLM-L6-v2` |
| **Process** | Embeds each chunk, stores in `port_tariffs` collection, batches of 50 |
| **Output** | ChromaDB collection (persisted in `data/chroma_db/`) |
| **When rebuilt** | `force_rebuild=True`, or collection missing/empty |

---

### Stage 4: Retrieval

| Component | `app/rag.py` → `retrieve_tariff_context_multi()` |
|-----------|--------------------------------------------------|
| **Input** | ChromaDB collection, vessel info, port |
| **Process** | Six targeted semantic queries, top 5 results each, deduplicated |
| **Queries** | See [Retrieval Queries](#retrieval-queries) below |
| **Output** | Concatenated tariff excerpts separated by `---` |
| **Fallbacks** | `retrieve_tariff_context()` (single broad query), then full PDF text[:35000] |

#### Retrieval Queries

```
1. "light dues calculation formula rate {port} GT {gt}, NT {nt}, LOA {loa}m, beam {beam}m"
2. "port dues berth dues calculation {port} gross tonnage net tonnage days alongside ..."
3. "towage dues tug charges {port} LOA beam draft ..."
4. "VTS vehicle traffic services dues {port} ..."
5. "pilotage dues pilot charges {port} LOA GT ..."
6. "running of vessel lines mooring line handling dues {port} ..."
```

---

### Stage 5: Prompt Construction

| Component | `app/tariff_calculator.py` → `format_vessel_context()`, `build_calculation_prompt()` |
|-----------|----------------------------------------------------------------------------------------|
| **Input** | `tariff_context` (retrieved text), `vessel` (VesselInfo), `port` |
| **Process** | Formats vessel parameters, builds full prompt with instructions |
| **Output** | Single prompt string for the LLM |
| **Prompt structure** | Role + tariff excerpts + vessel params + instructions + JSON schema hint |

---

### Stage 6: LLM Generation

| Component | `app/tariff_calculator.py` → `calculate_tariffs()` |
|-----------|----------------------------------------------------|
| **Input** | Full prompt, `generation_config` |
| **Technology** | Google Gemini (`gemini-2.5-flash` by default) |
| **Config** | `response_mime_type="application/json"`, `response_schema` with 6 required fields |
| **Output** | Raw response text (JSON object) |
| **Fallback** | If `response_schema` fails, uses plain `generate_content(prompt)` |

---

### Stage 7: Response Parsing

| Component | `app/tariff_calculator.py` → `parse_tariff_response()` |
|-----------|--------------------------------------------------------|
| **Input** | Raw LLM response string |
| **Process** | Removes markdown blocks, extracts JSON via regex, parses to dict |
| **Fallback** | If JSON fails, extracts 6 numbers in order and maps to keys |
| **Output** | `TariffResult` with all six tariffs as floats |

---

## 3. Data Flow

### Entry Points

| Entry Point | File | Calls |
|-------------|------|-------|
| CLI | `main.py` | `run_tariff_calculation(vessel, port, ...)` |
| API | `api.py` | `run_tariff_calculation(vessel, port)` |

### Orchestration (`app/service.py`)

```
run_tariff_calculation(vessel, port)
    │
    ├── get_tariff_pdf_path_or_raise()
    │
    ├── build_vector_store(force_rebuild)
    │       └── _build_collection() if needed
    │               ├── load_pdf_text(pdf_path)
    │               ├── chunk_text(text)
    │               └── collection.add(documents, ...)
    │
    ├── retrieve_tariff_context_multi(collection, vessel, port)
    │       └── [FALLBACK] retrieve_tariff_context(collection, query)
    │       └── [FALLBACK] load_pdf_text(pdf_path)[:35000]
    │
    └── calculate_tariffs(vessel, port, tariff_context, ...)
            ├── format_vessel_context(vessel, port)
            ├── build_calculation_prompt(vessel_context, tariff_context)
            ├── model.generate_content(prompt, generation_config)
            └── parse_tariff_response(response_text)
```

---

## 4. Module Reference

| Module | Key Functions | Responsibility |
|--------|---------------|----------------|
| `app/config.py` | `get_tariff_pdf_path_or_raise()`, `get_gemini_api_key()`, `get_gemini_model()` | Paths, env, model config |
| `app/models.py` | `VesselInfo.from_dict()`, `TariffResult.to_dict()` | Data models |
| `app/pdf_loader.py` | `load_pdf_text()`, `chunk_text()` | PDF extraction and chunking |
| `app/rag.py` | `build_vector_store()`, `retrieve_tariff_context()`, `retrieve_tariff_context_multi()` | Vector store and retrieval |
| `app/tariff_calculator.py` | `format_vessel_context()`, `build_calculation_prompt()`, `parse_tariff_response()`, `calculate_tariffs()` | Prompt building, LLM call, parsing |
| `app/service.py` | `run_tariff_calculation()` | Pipeline orchestration |
| `main.py` | `main()` | CLI entry point |
| `api.py` | `calculate()`, `calculate_raw()` | HTTP API entry points |

---

## 5. Configuration

| Setting | Environment Variable | Default | Description |
|---------|----------------------|---------|-------------|
| API Key | `GEMINI_API_KEY` | (required) | Google Gemini API key |
| Model | `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| PDF Path | (file location) | `data/port tariff.pdf` | Tariff document path |
| ChromaDB Path | (config) | `data/chroma_db/` | Vector store persistence |
| Chunk Size | (code) | 1500 | Characters per chunk |
| Chunk Overlap | (code) | 200 | Overlap between chunks |
| Top-K (single query) | (code) | 12 | Retrieved chunks for broad query |
| Top-K (multi query) | (code) | 5 | Retrieved chunks per tariff query |
| Fallback PDF Length | (code) | 35000 | Max chars when using full PDF as context |

---
