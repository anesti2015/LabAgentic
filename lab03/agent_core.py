"""agent_core.py - the reusable agent harness you build during Lab 3.

Ex1: complete execute_tool() and the TODOs in run_agent() (the guarded ReAct loop).
Ex2: complete the approval-policy TODO in run_agent().
Ex3: reuse run_agent() unchanged for the orchestrator.
"""
import inspect
import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client()
MODEL = os.getenv("LAB_MODEL", "gemini-3.5-flash-lite")  # fallback: gemini-3.1-flash-lite
# Experiment from the lab: LAB_TEMPERATURE=0 vs unset (Gemini 3 default 1.0, recommended by Google).
TEMPERATURE = float(os.environ["LAB_TEMPERATURE"]) if os.getenv("LAB_TEMPERATURE") else None


@dataclass
class AgentResult:
    answer: str
    stop_reason: str  # "done" | "max_steps" | "stuck" | "provider_error"
    steps: int
    prompt_tokens_per_step: list[int] = field(default_factory=list)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(self.prompt_tokens_per_step)


@dataclass
class Decision:
    """Ex2: what the human operator decided about a risky tool call."""
    approved: bool
    args: dict | None = None  # set when the operator EDITED the arguments
    feedback: str = ""        # free-text reason, sent back to the model


Approver = Callable[[str, dict], Decision]


def call_llm(contents, config, retries: int = 5):
    """One model call, with retry + exponential backoff on 429/5xx (given)."""
    for attempt in range(retries):
        try:
            return client.models.generate_content(model=MODEL, contents=contents, config=config)
        except errors.APIError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                wait = 2 ** attempt * 5
                print(f"  .. provider error {e.code}, retrying in {wait}s")
                time.sleep(wait)
            else:
                raise


def execute_tool(tools_map: dict[str, Callable], name: str, args: dict) -> str:
    """Gate: known tool? then run it. Every failure must become a readable string, never a crash."""
    if name not in tools_map:
        return f"ERROR: Unknown tool '{name}'. Available tools: {', '.join(tools_map)}."
    try:
        return str(tools_map[name](**args))
    except TypeError as e:  # tell the model what the correct call looks like, so it can self-heal
        return (f"ERROR: Bad arguments for {name}: {e}. "
                f"Expected: {name}{inspect.signature(tools_map[name])}, got: {json.dumps(args)}.")
    except Exception as e:  # noqa: BLE001 - errors are results, not crashes
        return f"ERROR: {name} failed: {e}"


def run_agent(
    user_prompt: str,
    tools: list[Callable],
    system_instruction: str,
    max_steps: int = 8,
    requires_approval: frozenset[str] = frozenset(),
    approver: Approver | None = None,
    show_thoughts: bool = False,
    verbose: bool = True,
) -> AgentResult:
    tools_map = {fn.__name__: fn for fn in tools}
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        # flash-lite thinks minimally by default; "high" + include_thoughts returns a readable summary.
        thinking_config=(types.ThinkingConfig(include_thoughts=True, thinking_level="high")
                         if show_thoughts else None),
        # No temperature override by default: Google recommends 1.0 for Gemini 3 models.
        temperature=TEMPERATURE,
    )
    messages = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]
    tokens: list[int] = []
    seen: Counter = Counter()

    for step in range(1, max_steps + 1):
        try:
            response = call_llm(messages, config)
        except errors.APIError as e:  # abnormal stop: report it, don't crash
            return AgentResult(f"STOPPED: provider error {e.code}: {e.message}", "provider_error", step, tokens)

        prompt_tokens = response.usage_metadata.prompt_token_count or 0
        tokens.append(prompt_tokens)
        if verbose:
            print(f"\n--- [Step {step}/{max_steps}] input tokens: {prompt_tokens:,} ---")
        content = response.candidates[0].content
        if verbose and content and content.parts:
            for part in content.parts:
                if part.thought and part.text:
                    print(f"  [Thought] {part.text.strip()[:300]}")

        # Stop condition A: no tool calls -> final answer
        if not response.function_calls:
            return AgentResult(response.text or "", "done", step, tokens)

        # 1. Append the model turn AS-IS (it carries Gemini 3 thought signatures)
        messages.append(content)

        parts = []
        for call in response.function_calls:
            args = dict(call.args or {})
            if verbose:
                print(f"  -> [Tool Call] {call.name}({json.dumps(args)[:200]})")

            # STRETCH (Ex1): stuck-agent detector. Count (name, sorted-args) in `seen`:
            #   2nd identical call -> output = "NOTE: Repeated call ... Use the earlier result."
            #   3rd identical call -> return AgentResult(..., "stuck", step, tokens)
            key = (call.name, json.dumps(args, sort_keys=True))
            seen[key] += 1
            if seen[key] >= 3:
                return AgentResult(
                    f"STOPPED: stuck - {call.name}({key[1]}) was requested {seen[key]} times with the same "
                    f"arguments. The earlier results did not move the task forward.",
                    "stuck", step, tokens,
                )

            if seen[key] == 2:  # not executed again: the answer is already in the history
                output = (f"NOTE: Repeated call {call.name}({key[1]}): you already have this result "
                          f"earlier in the conversation. Use the earlier result and move on.")
            # Ex2: policy layer - the approval gate lives in the HARNESS, not in the tool.
            elif call.name in requires_approval:
                decision = (approver(call.name, args) if approver is not None
                            else Decision(False, feedback="No approver configured"))
                if not decision.approved:
                    # A human decision is a tool RESULT, not a crash: the model reads it next step.
                    output = f"DENIED BY OPERATOR: {decision.feedback}. Adjust your plan."
                elif decision.args is not None:
                    output = execute_tool(tools_map, call.name, decision.args)
                    changed = {k: v for k, v in decision.args.items()
                               if k != "content" and args.get(k) != v}
                    output += f" NOTE: the operator edited your arguments: {json.dumps(changed)}"
                else:
                    output = execute_tool(tools_map, call.name, args)
            else:
                output = execute_tool(tools_map, call.name, args)

            if verbose:
                print(f"  <- [Tool Output] {output[:160]}")
            # Ex1: ONE function_response part per call (keep the call id)
            parts.append(types.Part(function_response=types.FunctionResponse(
                id=call.id, name=call.name, response={"result": output})))

        # Ex1: ALL parts in ONE message. Gemini has no "tool" role.
        messages.append(types.Content(role="user", parts=parts))

    # Stop condition B: budget exhausted -> partial progress, not a crash
    return AgentResult(
        f"STOPPED after {max_steps} steps without a final answer. Raise max_steps or narrow the task.",
        "max_steps", max_steps, tokens,
    )
