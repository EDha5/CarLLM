# Diagnostic Chat DB Schema

This document describes the Firestore schema for the diagnostic chat dashboard.

## Collections

### vehicle_catalog
Hierarchical catalog used to power dropdowns for Year → Make → Model → Submodel → Engine.
Each level is a collection of normalized, display-ready options scoped by the path above it.

#### vehicle_catalog/years/{yearId}
Doc id: `YYYY` (e.g., `2025`).

Fields:
- year (number)
- label (string; display value, usually same as year)
- sortOrder (number; ascending year for UI)
- makesCount (number, optional)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

#### vehicle_catalog/years/{yearId}/makes/{makeId}
Doc id: slug (e.g., `ford`, `mercedes-benz`).

Fields:
- makeId (string; slug)
- name (string; display label, e.g., "Mercedes-Benz")
- sortOrder (number; alpha or curated order)
- modelsCount (number, optional)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

#### vehicle_catalog/years/{yearId}/makes/{makeId}/models/{modelId}
Doc id: slug (e.g., `f-150`, `c-class`).

Fields:
- modelId (string; slug)
- name (string; display label, e.g., "F-150")
- sortOrder (number; alpha or curated order)
- submodelsCount (number, optional)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

#### vehicle_catalog/years/{yearId}/makes/{makeId}/models/{modelId}/submodels/{submodelId}
Doc id: slug (e.g., `xlt`, `limited`).

Fields:
- submodelId (string; slug)
- name (string; display label, e.g., "XLT")
- sortOrder (number; alpha or curated order)
- enginesCount (number, optional)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

#### vehicle_catalog/years/{yearId}/makes/{makeId}/models/{modelId}/submodels/{submodelId}/engines/{engineId}
Doc id: slug (e.g., `3-5l-v6-ecoboost`).

Fields:
- engineId (string; slug)
- name (string; display label, e.g., "3.5L V6 EcoBoost")
- displacementLiters (number, optional)
- cylinders (number, optional)
- fuelType (string, optional; gasoline|diesel|hybrid|electric|other)
- aspiration (string, optional; naturally_aspirated|turbo|supercharged|other)
- sortOrder (number; alpha or curated order)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

Notes:
- This structure optimizes dropdown queries: fetch the next level based on the user's current selection.
- If you need a direct lookup by VIN or full text search, add a separate flattened collection
  (e.g., `vehicle_variants`) rather than denormalizing dropdown nodes.

### cars
One document per vehicle.

Fields:
- userId (string)
- name (string)
- vin (string, optional)
- year (number or string)
- make (string)
- model (string)
- trim (string, optional)
- mileage (number, optional)
- engine (string, optional)
- transmission (string, optional)
- engineType (string, optional; extracted metadata from chat)
- transmissionType (string, optional; extracted metadata from chat)
- drivetrain (string, optional; e.g., FWD|RWD|AWD|4WD)
- fuelType (string, optional; gasoline|diesel|hybrid|electric|other)
- Replacements (array of strings, optional; parts the user reports replacing)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

### diagnostics
One document per diagnostic case. This is the parent for chats.

Fields:
- userId (string)
- carId (string or reference to cars doc)
- title (string)
- summary (string, optional)
- status (string: open|closed|archived)
- symptoms (array of strings, optional)
- dtcCodes (array of strings, optional)
- intakeAnswers (map, optional; structured intake responses)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)

### chats
One document per diagnostic case / conversation.

Fields:
- userId (string)
- diagnosticId (string)
- carId (string)
- status (string: open|closed|archived)
- phase (string: intake_questions|intake_answers|diagnosis_pending|normal)
- awaitingResponse (boolean)
- createdAt (number, ms timestamp)
- updatedAt (number, ms timestamp)
- firstPromptId (string or reference to messages doc)
- latestMessageId (string or reference to messages doc)
- summary (string, optional; rolling summary for long threads)

### chats/{chatId}/messages
All user + assistant messages in chronological order.

Fields:
- role (string: user|assistant|system)
- promptType (string: intake|aggregate|normal)
- content (string or structured JSON)
- createdAt (number, ms timestamp)
- source (string: user|llm|system)
- metadata (map, optional)
  - intakeStage (string: initial|followup_questions|followup_answer)
  - model (string, optional)
  - aggregationId (string, optional)
  - winnerModel (string, optional)
- parentMessageId (string, optional; for threading if needed)

### chats/{chatId}/llm_runs
Captures the multi-LLM fan-out for a single user prompt.

Fields:
- messageId (string or reference to triggering user message)
- model (string)
- provider (string)
- status (string: queued|running|completed|failed)
- promptType (string: aggregate)
- inputSnapshot (map: intake data, car context, system prompt version)
- output (string or structured JSON)
- createdAt (number, ms timestamp)
- finishedAt (number, ms timestamp)
- error (string, optional)

### chats/{chatId}/aggregations
Stores the combined response from multiple LLM runs.

Fields:
- messageId (string or reference to triggering user message)
- llmRunIds (array of references or strings)
- combinedOutput (string)
- strategy (string: judge|rank|merge|vote|summarize)
- winnerModel (string, optional)
- createdAt (number, ms timestamp)

## Prompt Types

### intake
The first prompt used to collect additional diagnostic data. Store both the user prompt
and the assistant follow-ups as messages with promptType: intake.

### aggregate
The fan-out step where multiple LLMs run, followed by a combined response.
Store raw outputs in llm_runs, the merged output in aggregations, and the user-facing
assistant reply as a message with promptType: aggregate.

### normal
All subsequent chat turns. Provide chat history + latest prompt to the LLM.

## Index Recommendations
- cars: (userId, createdAt desc)
- diagnostics: (carId, userId, createdAt desc)
- chats: (userId, updatedAt desc)
- chats: (diagnosticId)
- chats: (carId)
- messages: (chatId, createdAt)

## Notes
- Keep the linear chat in messages so the UI remains simple.
- Use summary on chats to manage long histories.
