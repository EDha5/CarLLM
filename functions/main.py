import json
import os
import re
import time
import logging
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

import requests
from firebase_admin import initialize_app, firestore
from firebase_functions import https_fn, firestore_fn

logger = logging.getLogger("carllm")

initialize_app()


@lru_cache(maxsize=1)
def _get_db():
    # Lazily initialize Firestore to avoid local import-time ADC failures.
    return firestore.client()

REQUEST_TIMEOUT = 360

FOLLOWUP_MODEL = "google/gemini-3-flash-preview"
CHAT_MODEL = "google/gemini-3-flash-preview"
FANOUT_MODELS = [
    "z-ai/glm-4.7",
    "minimax/minimax-m2.1",
    "x-ai/grok-4.1-fast",
]
AGGREGATOR_MODEL = "google/gemini-3-pro-preview"


class ProgressTracker:
    def __init__(self, ref, min_interval: float = 1.0):
        self._ref = ref
        self._min_interval = min_interval
        self._lock = Lock()
        self._pending = 0
        self._last_update = time.time()

    def add(self, delta: int, force: bool = False):
        if not delta and not force:
            return
        with self._lock:
            if delta:
                self._pending += delta
            now = time.time()
            should_flush = force or (now - self._last_update) >= self._min_interval
            if not should_flush or self._pending == 0:
                return
            to_flush = self._pending
            self._pending = 0
            self._last_update = now
        self._ref.update({"tokensReceived": firestore.Increment(to_flush)})


def _now_ms() -> int:
    return int(time.time() * 1000)


def _call_openrouter(
    api_key: str,
    model: str,
    messages,
    temperature: float = 0.3,
    response_format=None,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return (content or "").strip()


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\S+", text))


def _call_openrouter_stream(
    api_key: str,
    model: str,
    messages,
    temperature: float = 0.3,
    response_format=None,
    progress_tracker=None,
):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if response_format:
        payload["response_format"] = response_format

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        stream=True,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    content_parts = []
    tokens_received = 0
    usage_info = None

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        data_str = line[len("data:") :].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue
        usage_chunk = chunk.get("usage")
        if isinstance(usage_chunk, dict):
            usage_info = usage_chunk
        delta = (
            chunk.get("choices", [{}])[0]
            .get("delta", {})
            .get("content", "")
        )
        if delta:
            content_parts.append(delta)
            delta_tokens = _estimate_tokens(delta)
            tokens_received += delta_tokens
            if progress_tracker and delta_tokens:
                progress_tracker.add(delta_tokens)

    content = "".join(content_parts).strip()
    if progress_tracker:
        if usage_info and usage_info.get("completion_tokens") is not None:
            adjustment = usage_info.get("completion_tokens") - tokens_received
            if adjustment:
                progress_tracker.add(adjustment, force=True)
        else:
            progress_tracker.add(0, force=True)
    return content, usage_info


def _require_auth(request) -> str:
    if request.auth is None or request.auth.uid is None:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.UNAUTHENTICATED,
            "Unauthenticated",
        )
    return request.auth.uid


def _require_chat_owner(chat_ref, uid: str):
    chat_snapshot = chat_ref.get()
    if not chat_snapshot.exists:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.NOT_FOUND,
            "Chat not found",
        )
    chat_data = chat_snapshot.to_dict() or {}
    if chat_data.get("userId") != uid:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.PERMISSION_DENIED,
            "Forbidden",
        )
    return chat_data


def _fetch_car_data(car_id: str):
    if not car_id:
        return {}
    snapshot = _get_db().collection("cars").document(car_id).get()
    return snapshot.to_dict() if snapshot.exists else {}


def _load_messages(chat_ref):
    messages = []
    for snap in chat_ref.collection("messages").order_by("createdAt").stream():
        data = snap.to_dict()
        data["id"] = snap.id
        messages.append(data)
    return messages


def _extract_intake_context(messages):
    initial = ""
    answers = []
    questions = []

    intake_user = [
        msg
        for msg in messages
        if msg.get("promptType") == "intake" and msg.get("role") == "user"
    ]
    intake_assistant = [
        msg
        for msg in messages
        if msg.get("promptType") == "intake" and msg.get("role") == "assistant"
    ]

    for msg in intake_user:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        intake_stage = (msg.get("metadata") or {}).get("intakeStage")
        if intake_stage == "initial":
            initial = content
        elif intake_stage == "followup_answer":
            parsed = _parse_json_content(content)
            if parsed and isinstance(parsed, dict) and isinstance(parsed.get("answers"), list):
                for item in parsed["answers"]:
                    if isinstance(item, str) and item.strip():
                        answers.append(item.strip())
            else:
                answers.append(content)
        else:
            if not initial:
                initial = content
            else:
                answers.append(content)

    for msg in intake_assistant:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        parsed = _parse_json_content(content)
        if parsed and isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
            for item in parsed["questions"]:
                if isinstance(item, str) and item.strip():
                    questions.append(item.strip())
        else:
            questions.append(content)

    return {
        "initial": initial,
        "questions": questions,
        "answers": answers,
    }


def _parse_json_content(content: str):
    if not isinstance(content, str):
        return None
    trimmed = content.strip()
    if not trimmed:
        return None
    if trimmed.startswith("```"):
        lines = trimmed.split("\n")
        lines.pop(0)
        if lines and lines[-1].strip().startswith("```"):
            lines.pop()
        trimmed = "\n".join(lines).strip()
    if not trimmed.startswith("{") or not trimmed.endswith("}"):
        return None
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return None


def _question_response_format(name: str = "followup_questions"):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "description": "Short, single-focus diagnostic questions",
                        "items": {"type": "string"},
                    }
                },
                "required": ["questions"],
                "additionalProperties": False,
            },
        },
    }


def _build_questions_payload(questions):
    cleaned = []
    for item in questions or []:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
    if not cleaned:
        cleaned = [
            "What symptoms are you noticing, and when did they start?",
            "Are there any warning lights or codes?",
            "Does anything make the issue better or worse?",
        ]
    return json.dumps({"questions": cleaned})


def _vehicle_metadata_response_format():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "vehicle_metadata_update",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "has_update": {"type": "boolean"},
                    "confidence": {
                        "type": "number",
                        "description": "Confidence from 0 to 1 that updates are correct",
                    },
                    "updates": {
                        "type": "object",
                        "properties": {
                            "engine_type": {"type": "string"},
                            "transmission_type": {"type": "string"},
                            "drivetrain": {"type": "string"},
                            "fuel_type": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["has_update", "confidence", "updates"],
                "additionalProperties": False,
            },
        },
    }


def _replacement_response_format():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "vehicle_replacements_update",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "has_update": {"type": "boolean"},
                    "confidence": {
                        "type": "number",
                        "description": "Confidence from 0 to 1 that updates are correct",
                    },
                    "replacements": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["has_update", "confidence", "replacements"],
                "additionalProperties": False,
            },
        },
    }


def _normalize_vehicle_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _extract_user_vehicle_text(content: str) -> str:
    parsed = _parse_json_content(content)
    if parsed and isinstance(parsed, dict):
        answers = parsed.get("answers")
        if isinstance(answers, list):
            clean_answers = [str(item).strip() for item in answers if str(item).strip()]
            if clean_answers:
                return "User answers:\n- " + "\n- ".join(clean_answers)
    return content.strip()


@https_fn.on_request(invoker="public")
def hello(request):
    return https_fn.Response("CARLLM Functions online.")


@https_fn.on_call(secrets=["OPENROUTER_API_KEY"], invoker="public")
def question_prompt(request):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "Missing OPENROUTER_API_KEY",
        )

    uid = _require_auth(request)
    payload = request.data or {}
    chat_id = payload.get("chatId")
    message_id = payload.get("messageId")

    if not chat_id or not message_id:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            "Missing chatId or messageId",
        )

    chat_ref = _get_db().collection("chats").document(chat_id)
    chat_data = _require_chat_owner(chat_ref, uid)
    chat_ref.update({"tokensReceived": 0, "updatedAt": _now_ms()})
    chat_ref.update({"tokensReceived": 0, "updatedAt": _now_ms()})

    message_snapshot = chat_ref.collection("messages").document(message_id).get()
    if not message_snapshot.exists:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.NOT_FOUND,
            "Message not found",
        )

    message_data = message_snapshot.to_dict()
    description = (message_data.get("content") or "").strip()
    if not description:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            "Missing description",
        )

    car_data = _fetch_car_data(chat_data.get("carId"))

    system_prompt = (
        "You are an automotive diagnostic assistant. Ask concise, high-signal follow-up "
        "questions to clarify symptoms. Always ask for mileage if it was not provided. "
        "Ask 3-6 questions max."
    )
    user_prompt = (
        "User description:\n"
        f"{description}\n\n"
        "Car info:\n"
        f"Year: {car_data.get('year', 'unknown')}\n"
        f"Make: {car_data.get('make', 'unknown')}\n"
        f"Model: {car_data.get('model', 'unknown')}\n"
        f"Mileage: {car_data.get('mileage', 'unknown')}\n"
    )

    progress_tracker = ProgressTracker(chat_ref)
    response_format = _question_response_format("intake_questions")
    try:
        content, _ = _call_openrouter_stream(
            api_key,
            FOLLOWUP_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            progress_tracker=progress_tracker,
            response_format=response_format,
        )
    except requests.RequestException:
        chat_ref.update(
            {
                "awaitingResponse": False,
                "updatedAt": _now_ms(),
            }
        )
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "OpenRouter request failed",
        )

    parsed = _parse_json_content(content)
    if parsed and isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        content = json.dumps(parsed)
    else:
        content = _build_questions_payload([content])

    assistant_ref = chat_ref.collection("messages").document()
    assistant_ref.set(
        {
            "role": "assistant",
            "promptType": "intake",
            "content": content or "No response generated.",
            "createdAt": _now_ms(),
            "source": "llm",
            "metadata": {
                "model": FOLLOWUP_MODEL,
                "intakeStage": "followup_questions",
            },
        }
    )
    chat_ref.update(
        {
            "awaitingResponse": False,
            "phase": "intake_answers",
            "updatedAt": _now_ms(),
            "latestMessageId": assistant_ref.id,
        }
    )

    return {"status": "ok"}


@https_fn.on_call(timeout_sec=360, secrets=["OPENROUTER_API_KEY"], invoker="public")
def fanout_diagnosis(request):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "Missing OPENROUTER_API_KEY",
        )

    uid = _require_auth(request)
    payload = request.data or {}
    chat_id = payload.get("chatId")
    message_id = payload.get("messageId")

    if not chat_id or not message_id:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            "Missing chatId or messageId",
        )

    chat_ref = _get_db().collection("chats").document(chat_id)
    chat_data = _require_chat_owner(chat_ref, uid)

    message_snapshot = chat_ref.collection("messages").document(message_id).get()
    if not message_snapshot.exists:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.NOT_FOUND,
            "Message not found",
        )

    car_data = _fetch_car_data(chat_data.get("carId"))
    messages = _load_messages(chat_ref)
    intake = _extract_intake_context(messages)

    if not intake["initial"]:
        chat_ref.update({"awaitingResponse": False, "updatedAt": _now_ms()})
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.FAILED_PRECONDITION,
            "Missing intake context",
        )

    car_text = (
        "Vehicle context:\n"
        f"Year: {car_data.get('year', 'unknown')}\n"
        f"Make: {car_data.get('make', 'unknown')}\n"
        f"Model: {car_data.get('model', 'unknown')}\n"
        f"Mileage: {car_data.get('mileage', 'unknown')}\n"
    )
    intake_text = (
        f"{car_text}\n"
        "Initial report:\n"
        f"{intake['initial']}\n\n"
        "Follow-up questions:\n"
        f"{chr(10).join(intake['questions']) or 'None'}\n\n"
        "User answers:\n"
        f"{chr(10).join(intake['answers']) or 'None'}"
    )

    progress_tracker = ProgressTracker(chat_ref)

    sufficiency_system = (
        "You are a master automotive diagnostician. Decide if the intake provides "
        "enough information to confidently choose a single diagnosis. Only say it is "
        "sufficient when you are very confident. If insufficient, ask 3-6 more focused "
        "questions, one question per item."
    )
    sufficiency_user = intake_text
    sufficiency_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "diagnosis_sufficiency",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "is_sufficient": {"type": "boolean"},
                    "confidence": {
                        "type": "number",
                        "description": "Confidence from 0 to 1 that a single diagnosis is correct",
                    },
                    "followup_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["is_sufficient", "confidence", "followup_questions"],
                "additionalProperties": False,
            },
        },
    }
    try:
        sufficiency_raw, _ = _call_openrouter_stream(
            api_key,
            AGGREGATOR_MODEL,
            [
                {"role": "system", "content": sufficiency_system},
                {"role": "user", "content": sufficiency_user},
            ],
            temperature=0.1,
            response_format=sufficiency_format,
            progress_tracker=progress_tracker,
        )
        sufficiency = _parse_json_content(sufficiency_raw) or {}
    except requests.RequestException:
        chat_ref.update({"awaitingResponse": False, "updatedAt": _now_ms()})
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "OpenRouter request failed",
        )

    is_sufficient = bool(sufficiency.get("is_sufficient"))
    confidence = sufficiency.get("confidence")
    followup_questions = sufficiency.get("followup_questions") or []

    if not isinstance(confidence, (int, float)):
        confidence = 0.0

    if (not is_sufficient) or confidence < 0.85:
        question_payload = _build_questions_payload(followup_questions)
        assistant_ref = chat_ref.collection("messages").document()
        assistant_ref.set(
            {
                "role": "assistant",
                "promptType": "intake",
                "content": question_payload,
                "createdAt": _now_ms(),
                "source": "llm",
                "metadata": {
                    "model": AGGREGATOR_MODEL,
                    "intakeStage": "followup_questions",
                },
            }
        )
        chat_ref.update(
            {
                "awaitingResponse": False,
                "phase": "intake_answers",
                "updatedAt": _now_ms(),
                "latestMessageId": assistant_ref.id,
            }
        )
        return {"status": "needs_more_info"}

    system_prompt = (
        "You are an automotive diagnostic assistant. Provide a concise diagnosis, "
        "likely root causes, and the next 2-3 checks to confirm. Be specific."
    )
    user_prompt = intake_text

    base_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    llm_run_refs = []
    for model in FANOUT_MODELS:
        run_ref = chat_ref.collection("llm_runs").document()
        run_ref.set(
            {
                "messageId": message_id,
                "model": model,
                "provider": model.split("/")[0],
                "status": "queued",
                "promptType": "aggregate",
                "inputSnapshot": {
                    "car": {
                        "year": car_data.get("year"),
                        "make": car_data.get("make"),
                        "model": car_data.get("model"),
                        "mileage": car_data.get("mileage"),
                    },
                    "intake": intake,
                },
                "createdAt": _now_ms(),
            }
        )
        llm_run_refs.append((model, run_ref))

    def run_model(model, run_ref):
        run_ref.update({"status": "running"})
        try:
            output, _ = _call_openrouter_stream(
                api_key,
                model,
                base_messages,
                temperature=0.2,
                progress_tracker=progress_tracker,
            )
            run_ref.update(
                {
                    "status": "completed",
                    "output": output,
                    "finishedAt": _now_ms(),
                }
            )
            return {"model": model, "output": output, "id": run_ref.id}
        except requests.RequestException as exc:
            run_ref.update(
                {
                    "status": "failed",
                    "error": str(exc),
                    "finishedAt": _now_ms(),
                }
            )
            return {"model": model, "output": "", "id": run_ref.id}

    results = []
    with ThreadPoolExecutor(max_workers=len(FANOUT_MODELS)) as executor:
        futures = [executor.submit(run_model, model, ref) for model, ref in llm_run_refs]
        for future in as_completed(futures):
            results.append(future.result())

    candidate_sections = []
    for result in results:
        candidate_sections.append(
            f"Model: {result['model']}\nResponse:\n{result['output'] or 'No response.'}"
        )

    judge_system = (
        "You are a master automotive diagnostician. Review the candidate diagnoses and "
        "select the most accurate given the intake data. Return JSON with keys "
        "`model_name`, `diagnostic_answer`, `justifacation`, and `explanation`. "
        "`diagnostic_answer` must be a short title only (no full explanation). "
        "`justifacation` must be an array of brief bullet-point strings."
    )
    judge_user = (
        f"{intake_text}\n\nCandidate diagnoses:\n\n" + "\n\n".join(candidate_sections)
    )

    combined_output = ""
    winner_model = None
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "diagnosis_judgement",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "The winning model identifier",
                    },
                    "diagnostic_answer": {
                        "type": "string",
                        "description": "Short title of what is wrong with the car",
                    },
                    "justifacation": {
                        "type": "array",
                        "description": "Bullet point reasons supporting the diagnosis",
                        "items": {"type": "string"},
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Concise explanation for the user",
                    },
                },
                "required": [
                    "model_name",
                    "diagnostic_answer",
                    "justifacation",
                    "explanation",
                ],
                "additionalProperties": False,
            },
        },
    }

    try:
        aggregation_raw, _ = _call_openrouter_stream(
            api_key,
            AGGREGATOR_MODEL,
            [
                {"role": "system", "content": judge_system},
                {"role": "user", "content": judge_user},
            ],
            temperature=0.2,
            response_format=response_format,
            progress_tracker=progress_tracker,
        )
        try:
            parsed = json.loads(aggregation_raw)
            winner_model = parsed.get("model_name") or parsed.get("modelName")
            combined_output = json.dumps(parsed)
        except json.JSONDecodeError:
            combined_output = aggregation_raw
    except requests.RequestException:
        chat_ref.update({"awaitingResponse": False, "updatedAt": _now_ms()})
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "OpenRouter request failed",
        )

    if not combined_output:
        combined_output = "Unable to determine a diagnosis at this time."

    aggregation_ref = chat_ref.collection("aggregations").document()
    aggregation_ref.set(
        {
            "messageId": message_id,
            "llmRunIds": [result["id"] for result in results],
            "combinedOutput": combined_output,
            "strategy": "judge",
            "winnerModel": winner_model,
            "createdAt": _now_ms(),
        }
    )

    assistant_ref = chat_ref.collection("messages").document()
    assistant_ref.set(
        {
            "role": "assistant",
            "promptType": "aggregate",
            "content": combined_output,
            "createdAt": _now_ms(),
            "source": "llm",
            "metadata": {
                "model": AGGREGATOR_MODEL,
                "winnerModel": winner_model,
                "aggregationId": aggregation_ref.id,
            },
        }
    )

    chat_ref.update(
        {
            "awaitingResponse": False,
            "phase": "normal",
            "updatedAt": _now_ms(),
            "latestMessageId": assistant_ref.id,
        }
    )

    return {"status": "ok"}


@https_fn.on_call(secrets=["OPENROUTER_API_KEY"], invoker="public")
def chat_reply(request):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "Missing OPENROUTER_API_KEY",
        )

    uid = _require_auth(request)
    payload = request.data or {}
    chat_id = payload.get("chatId")
    message_id = payload.get("messageId")

    if not chat_id or not message_id:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            "Missing chatId or messageId",
        )

    chat_ref = _get_db().collection("chats").document(chat_id)
    _require_chat_owner(chat_ref, uid)
    chat_ref.update({"tokensReceived": 0, "updatedAt": _now_ms()})

    message_snapshot = chat_ref.collection("messages").document(message_id).get()
    if not message_snapshot.exists:
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.NOT_FOUND,
            "Message not found",
        )

    messages = _load_messages(chat_ref)
    history = []
    for msg in messages:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})

    system_prompt = (
        "You are an automotive diagnostic assistant. Use the full conversation "
        "context and answer the latest user question clearly and concisely."
    )
    full_messages = [{"role": "system", "content": system_prompt}, *history]

    progress_tracker = ProgressTracker(chat_ref)
    try:
        content, _ = _call_openrouter_stream(
            api_key,
            CHAT_MODEL,
            full_messages,
            temperature=0.3,
            progress_tracker=progress_tracker,
        )
    except requests.RequestException:
        chat_ref.update({"awaitingResponse": False, "updatedAt": _now_ms()})
        raise https_fn.HttpsError(
            https_fn.FunctionsErrorCode.INTERNAL,
            "OpenRouter request failed",
        )

    assistant_ref = chat_ref.collection("messages").document()
    assistant_ref.set(
        {
            "role": "assistant",
            "promptType": "normal",
            "content": content or "No response generated.",
            "createdAt": _now_ms(),
            "source": "llm",
            "metadata": {"model": CHAT_MODEL},
        }
    )

    chat_ref.update(
        {
            "awaitingResponse": False,
            "phase": "normal",
            "updatedAt": _now_ms(),
            "latestMessageId": assistant_ref.id,
        }
    )

    return {"status": "ok"}


@firestore_fn.on_document_created(
    document="chats/{chatId}/messages/{messageId}",
    secrets=["OPENROUTER_API_KEY"],
)
def enrich_vehicle_metadata(event):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("metadata: missing OPENROUTER_API_KEY")
        return

    snapshot = event.data
    if snapshot is None:
        logger.warning("metadata: missing snapshot data")
        return
    message = snapshot.to_dict() or {}
    if message.get("role") != "user":
        logger.info("metadata: skipping non-user message")
        return

    content = (message.get("content") or "").strip()
    if not content:
        logger.info("metadata: empty message content")
        return

    params = getattr(event, "params", {}) or {}
    chat_id = params.get("chatId")
    if not chat_id:
        logger.warning("metadata: missing chatId in event params")
        return

    chat_ref = _get_db().collection("chats").document(chat_id)
    chat_snapshot = chat_ref.get()
    if not chat_snapshot.exists:
        logger.warning("metadata: chat not found", extra={"chatId": chat_id})
        return
    chat_data = chat_snapshot.to_dict() or {}

    car_id = chat_data.get("carId")
    if not car_id:
        logger.info("metadata: chat missing carId", extra={"chatId": chat_id})
        return

    car_ref = _get_db().collection("cars").document(car_id)
    car_snapshot = car_ref.get()
    if not car_snapshot.exists:
        logger.warning("metadata: car not found", extra={"carId": car_id})
        return
    car_data = car_snapshot.to_dict() or {}

    known_engine = _normalize_vehicle_text(car_data.get("engineType"))
    known_transmission = _normalize_vehicle_text(car_data.get("transmissionType"))
    known_drivetrain = _normalize_vehicle_text(car_data.get("drivetrain"))
    known_fuel = _normalize_vehicle_text(car_data.get("fuelType"))

    message_text = _extract_user_vehicle_text(content)
    logger.info(
        "metadata: evaluating message",
        extra={"carId": car_id, "chatId": chat_id},
    )

    system_prompt = (
        "You extract vehicle identity metadata from user messages. "
        "Only return updates if the user explicitly states the information. "
        "Do not guess. Use the current known data to avoid duplicates."
    )
    user_prompt = (
        "Known vehicle:\n"
        f"Year: {car_data.get('year', 'unknown')}\n"
        f"Make: {car_data.get('make', 'unknown')}\n"
        f"Model: {car_data.get('model', 'unknown')}\n"
        f"Known engine_type: {known_engine or 'unknown'}\n"
        f"Known transmission_type: {known_transmission or 'unknown'}\n"
        f"Known drivetrain: {known_drivetrain or 'unknown'}\n"
        f"Known fuel_type: {known_fuel or 'unknown'}\n\n"
        "User message:\n"
        f"{message_text}"
    )

    try:
        response = _call_openrouter(
            api_key,
            AGGREGATOR_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format=_vehicle_metadata_response_format(),
        )
    except requests.RequestException:
        logger.exception("metadata: OpenRouter request failed")
        return

    parsed = _parse_json_content(response)
    if not parsed or not isinstance(parsed, dict):
        logger.warning("metadata: invalid JSON response")
        return

    if not parsed.get("has_update"):
        logger.info("metadata: no update suggested")
        return

    confidence = parsed.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0.8:
        logger.info("metadata: low confidence", extra={"confidence": confidence})
        return

    updates = parsed.get("updates") or {}
    if not isinstance(updates, dict):
        logger.warning("metadata: updates not a dict")
        return

    field_map = {
        "engine_type": "engineType",
        "transmission_type": "transmissionType",
        "drivetrain": "drivetrain",
        "fuel_type": "fuelType",
    }
    write_updates = {}
    for source_key, target_key in field_map.items():
        value = _normalize_vehicle_text(updates.get(source_key))
        if not value:
            continue
        if value == _normalize_vehicle_text(car_data.get(target_key)):
            continue
        write_updates[target_key] = value

    if not write_updates:
        logger.info("metadata: no new fields to write")
        return

    write_updates["updatedAt"] = _now_ms()
    car_ref.update(write_updates)
    logger.info(
        "metadata: updated car record",
        extra={"carId": car_id, "updates": write_updates},
    )


@firestore_fn.on_document_created(
    document="chats/{chatId}/messages/{messageId}",
    secrets=["OPENROUTER_API_KEY"],
)
def enrich_vehicle_replacements(event):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("replacements: missing OPENROUTER_API_KEY")
        return

    snapshot = event.data
    if snapshot is None:
        logger.warning("replacements: missing snapshot data")
        return
    message = snapshot.to_dict() or {}
    if message.get("role") != "user":
        logger.info("replacements: skipping non-user message")
        return

    content = (message.get("content") or "").strip()
    if not content:
        logger.info("replacements: empty message content")
        return

    params = getattr(event, "params", {}) or {}
    chat_id = params.get("chatId")
    if not chat_id:
        logger.warning("replacements: missing chatId in event params")
        return

    chat_ref = _get_db().collection("chats").document(chat_id)
    chat_snapshot = chat_ref.get()
    if not chat_snapshot.exists:
        logger.warning("replacements: chat not found", extra={"chatId": chat_id})
        return
    chat_data = chat_snapshot.to_dict() or {}

    car_id = chat_data.get("carId")
    if not car_id:
        logger.info("replacements: chat missing carId", extra={"chatId": chat_id})
        return

    car_ref = _get_db().collection("cars").document(car_id)
    car_snapshot = car_ref.get()
    if not car_snapshot.exists:
        logger.warning("replacements: car not found", extra={"carId": car_id})
        return
    car_data = car_snapshot.to_dict() or {}

    existing_replacements = car_data.get("Replacements") or []
    if not isinstance(existing_replacements, list):
        existing_replacements = []
    existing_normalized = {str(item).strip().lower() for item in existing_replacements}

    message_text = _extract_user_vehicle_text(content)
    logger.info(
        "replacements: evaluating message",
        extra={"carId": car_id, "chatId": chat_id},
    )

    system_prompt = (
        "You extract replacement parts from user messages. "
        "Only return replacements if the user explicitly says a part was replaced, "
        "installed, or swapped. Do not guess."
    )
    user_prompt = (
        "Known replacements:\n"
        f"{', '.join(existing_replacements) if existing_replacements else 'None'}\n\n"
        "User message:\n"
        f"{message_text}"
    )

    try:
        response = _call_openrouter(
            api_key,
            AGGREGATOR_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format=_replacement_response_format(),
        )
    except requests.RequestException:
        logger.exception("replacements: OpenRouter request failed")
        return

    parsed = _parse_json_content(response)
    if not parsed or not isinstance(parsed, dict):
        logger.warning("replacements: invalid JSON response")
        return

    if not parsed.get("has_update"):
        logger.info("replacements: no update suggested")
        return

    confidence = parsed.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0.8:
        logger.info("replacements: low confidence", extra={"confidence": confidence})
        return

    replacements = parsed.get("replacements") or []
    if not isinstance(replacements, list):
        logger.warning("replacements: replacements not a list")
        return

    additions = []
    for item in replacements:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in existing_normalized:
            continue
        existing_normalized.add(normalized)
        additions.append(cleaned)

    if not additions:
        logger.info("replacements: no new replacements to add")
        return

    updated_replacements = existing_replacements + additions
    car_ref.update(
        {
            "Replacements": updated_replacements,
            "updatedAt": _now_ms(),
        }
    )
    logger.info(
        "replacements: updated car record",
        extra={"carId": car_id, "additions": additions},
    )
