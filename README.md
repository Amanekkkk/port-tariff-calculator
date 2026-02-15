# Port Tariff Calculation Task

## Overview
The candidate is expected to email their solution latest by Monday morning (i.e, within 2.5 days from now). The candidate can use one of the Gemini LLMs for this task, as they have a free tier with generous rate limit. Please confirm that the candidate has received the email/task, and please do let me know if you have any questions or need clarifications.

Attached is a South African port tariff document that contains information on how different tariffs are calculated. I want you to build a solution (can be a RAG application, can be an agentic workflow, or anything else that you may decide, with any framework of your choice) that takes a user query containing the vessel parameters and automates calculation of the following tariffs from it:

- light dues
- port dues
- towage dues
- vehicle traffic services (VTS) dues
- pilotage dues
- running of vessel lines dues

The tariff calculations will depend on several vessel parameters and the specific port where the vessel arrives, so the user query will look something like this:

"Calculate the different tariffs payable by the following vessel berthing at the port of <Durban | Saldanha | Richard's Bay>:

<vessel_info>"

## Example Vessel Info
Here is an example vessel info that you can use for the port of Durban, so that you can verify the calculations of your solution with the ground truth:

**Vessel Details: General**
- **Vessel Name:** SUDESTADA
- **Built:** 2010
- **Flag:** MLT - Malta
- **Classification Society:** Registro Italiano Navale
- **Call Sign:** [Not provided]

**Main Details**
- **Lloyds / IMO No.:** [Not provided]
- **Type:** Bulk Carrier
- **DWT:** 93,274
- **GT / NT:** 51,300 / 31,192
- **LOA (m):** 229.2
- **Beam (m):** 38
- **Moulded Depth (m):** 20.7
- **LBP:** 222
- **Drafts SW S / W / T (m):** 14.9 / 0 / 0
- **Suez GT / NT:** - / 49,069

**Communication**
- **E-mail:** [Not provided]
- **Commercial E-mail:** [Not provided]

**DRY**
- **Number of Holds:** 7

**Cargo Details**
- **Cargo Quantity:** 40,000 MT
- **Days Alongside:** 3.39 days
- **Arrival Time:** 15 Nov 2024 10:12
- **Departure Time:** 22 Nov 2024 13:00

**Activity/Operations**
- **Activity:** Exporting Iron Ore
- **Number of Operations:** 2

## How to Run

### Prerequisites

- Python 3.10+
- [Gemini API key](https://aistudio.google.com/apikey) (free tier)

### Setup

1. **Clone the repository and install dependencies:**

   ```bash
   cd test_anderson
   pip install -r requirements.txt
   ```

2. **Set your Gemini API key:**

   ```bash
   export GEMINI_API_KEY=your_api_key_here
   # Or create a .env file with GEMINI_API_KEY=...
   ```

   If you get 404 "model not found" or 429 "quota exceeded" (limit 0), override the model:
   ```bash
   export GEMINI_MODEL=gemini-2.5-flash
   # Free tier models: gemini-2.5-flash, gemini-2.5-flash-lite, gemini-3-flash-preview
   # See https://ai.google.dev/gemini-api/docs/rate-limits for current quotas
   ```

3. **Place the port tariff PDF** in the `data/` folder:

   ```
   data/port tariff.pdf
   ```

   The PDF should be the South African port tariff document containing the rules for light dues, port dues, towage, VTS, pilotage, and running of vessel lines.

### Run the CLI

```bash
# Calculate tariffs for the example vessel (SUDESTADA at Durban)
python main.py

# Specify custom vessel file and port
python main.py --vessel data/example_vessel.json --port Durban

# Output as JSON
python main.py --output json

# Force rebuild of vector index (after updating the PDF)
python main.py --rebuild
```

### Run the API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

**API endpoints:**

- `GET /health` – Health check
- `POST /calculate` – Calculate tariffs (see example below)
- `POST /calculate/raw` – Calculate from flexible JSON body

**Example API request:**

```bash
curl -X POST http://localhost:8000/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "vessel": {
      "name": "SUDESTADA",
      "vessel_type": "Bulk Carrier",
      "gt": 51300,
      "nt": 31192,
      "dwt": 93274,
      "loa": 229.2,
      "beam": 38,
      "days_aside": 3.39,
      "cargo_quantity": 40000,
      "number_of_operations": 2
    },
    "port": "Durban"
  }'
```

**Example response:**

```json
{
  "light_dues": 60062.04,
  "port_dues": 199549.22,
  "towage_dues": 147074.38,
  "vehicle_traffic_services_vts_dues": 33315.75,
  "pilotage_dues": 47189.94,
  "running_of_vessel_lines_dues": 19639.50
}
```

### Project Structure

```
test_anderson/
├── app/
│   ├── config.py          # Configuration
│   ├── models.py          # VesselInfo, TariffResult
│   ├── pdf_loader.py      # PDF text extraction
│   ├── rag.py             # Vector store & retrieval
│   ├── tariff_calculator.py  # Gemini LLM tariff calculation
│   └── service.py         # Main orchestration
├── data/
│   ├── port tariff.pdf    # Place the tariff PDF here
│   └── example_vessel.json
├── main.py                # CLI entry point
├── api.py                 # FastAPI endpoint
└── requirements.txt
```

### Solution Overview

This solution uses a **RAG (Retrieval-Augmented Generation)** approach:

1. The port tariff PDF is loaded and chunked into smaller segments.
2. Chunks are embedded and stored in a ChromaDB vector store.
3. For each calculation request, relevant tariff rules are retrieved based on the vessel parameters and port.
4. The Gemini LLM receives the retrieved context and vessel info, then calculates the tariffs using the document rules.
5. Results are parsed and returned in a structured format.

---

## Submission Requirements
Your solution is expected to be a GitHub repo with clear instructions in a Readme file on how to run the script(s) with the output being the different tariff values. Bonus points if you can deploy it as an API endpoint, with proper instructions on how to consume it.

## Scoring Criteria
- **Accuracy of tariff calculations** – how many tariffs your solution can calculate correctly, how much deviation is there from the correct values, etc.
- **Level of automation** – how accurate are your calculated values with the least amount of manual prompting to the LLM explicitly of how to calculate the individual tariffs.
- **Code quality** – modular, refactored, micro-service, etc wherever applicable and whether your code runs smoothly without any debugging needed from our side.

## Ground Truth (for Verification)
To help you verify your calculations for the aforementioned vessel, here are the correct values of the tariffs:

* **light dues:** ZAR 60,062.04
* **port dues:** ZAR 199,549.22
* **towage dues:** ZAR 147,074.38
* **vehicle traffic services (VTS) dues:** ZAR 33,315.75
* **pilotage dues:** ZAR 47,189.94
* **running of vessel lines dues:** ZAR 19,639.50