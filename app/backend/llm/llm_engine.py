# backend/llm/llm_engine.py
"""
LLM Engine wrapper.

IMPORTANT:
- Prompt format must NEVER change unless the model is retrained.
- Summary text must be passed verbatim from severity.py.
"""

DEBUG = False
USE_STUB = False   # Set True to bypass LLM for UI testing

# The 'coach' object should be initialized externally if using llama.cpp
coach = None


def _log(msg):
    if DEBUG:
        print(f"[LLM_ENGINE] {msg}")



def init_llm(model):
    """
    Injects the LLM instance (llama.cpp / GGUF).
    Call this ONCE during app startup.
    """
    global coach
    coach = model
    _log("LLM initialized")

# def is_initialized():
#     return coach is not None


def get_coaching_feedback(summary: str, severity: str, is_coach: bool) -> str:
    """
    Main entry point used by UI and services.
    """
    print(">>> ENTERED get_coaching_feedback")

    if USE_STUB:
        return _stub_response(summary)

    if coach is None:
        raise RuntimeError("LLM not initialized. Call init_llm() first.")

    prompt = _build_prompt(summary)

    _log("Sending prompt to LLM")

    if severity == "LOW":
        output = coach(
        prompt,
        max_tokens=200,
        temperature=1.0,
        top_p=1.0,
        repeat_penalty=1.1,
        stop=["<|eot_id|>","<|start_header_id|>"]
    )
    if severity == "MEDIUM":
        output = coach(
        prompt,
        max_tokens=200,
        temperature=0.8,
        top_p=0.9,
        repeat_penalty=1.2,
        stop=["<|eot_id|>","<|start_header_id|>"]
    )
    if severity == "HIGH":
        output = coach(
        prompt,
        max_tokens=300,
        temperature=0.3, # high temperature for creative long responses
        top_p=0.8, # low prob low for controlling variety of words
        repeat_penalty=1.2,
        stop=["<|eot_id|>","<|start_header_id|>"]
    )
    print(">>> RAW RESULT TYPE:", type(output))
    print(">>> RAW RESULT:", output)
    text = output["choices"][0]["text"]

    replacements = {
        "segment": "trip",
        "Segment": "Trip",
        "this segment": "this trip",
        "the segment": "the Trip",
    }
    if is_coach:
        for word, replacement in replacements.items():
            text = text.replace(word, replacement)

    return text.strip()


# ================= INTERNAL HELPERS =================


def _build_prompt(summary: str) -> str:
    """
    EXACT prompt used during training.
    DO NOT MODIFY.
    """

    return (
        "<|start_header_id|>system<|end_header_id|>\n\n"
        "You are an expert driving coach. Analyze EVERY item in the sensor data. "
        "Give SPECIFIC feedback on harsh brakes, accelerations, corners, bumps, jerk, "
        "and speed variance. Be honest about issues but encouraging. Always mention "
        "detected events. <|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n\n"
        f"{summary}"
        "<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\n"
    )


def _extract_response(output: str) -> str:
    """
    Extracts assistant response safely.
    """

    marker = "<|start_header_id|>assistant<|end_header_id|>\n\n"
    if marker in output:
        text = output.split(marker)[-1]
        text = text.split("<|eot_id|>")[0]
        return text.strip()

    # fallback (should not happen)
    return output.strip()


def _stub_response(summary: str) -> str:
    """
    Deterministic response for UI wiring & debugging.
    """

    return (
        "This is a stubbed coaching response.\n\n"
        "Detected driving events:\n"
        "- Harsh braking and acceleration patterns observed\n"
        "- Speed variations present\n\n"
        "Use real LLM for actual feedback."
    )