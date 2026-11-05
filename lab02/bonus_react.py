import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from module3_tools import lookup_cve_details  # reuse the tool from Ex. 3

load_dotenv()
client = genai.Client()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_ITERATIONS = 5


def get_installed_packages(hostname: str) -> str:
    """Return the list of installed packages (name and version) on a given host.

    Args:
        hostname: The server hostname, for example 'db-prod-01'.
    """
    inventory = {
        "db-prod-01": ["openssh-server 9.6", "xz-utils 5.6.1", "postgresql 16"],
    }
    packages = inventory.get(hostname.lower())
    if packages is None:
        return json.dumps({"error": f"Unknown host {hostname}"})
    return json.dumps({"hostname": hostname, "packages": packages})


# Registry: tool name -> local Python function
TOOLS = {
    "lookup_cve_details": lookup_cve_details,
    "get_installed_packages": get_installed_packages,
}


def run_tool(name: str, args: dict) -> str:
    """Execute a tool requested by the model. Errors are returned to the model, never raised."""
    func = TOOLS.get(name)
    if func is None:
        # Unknown tool -> tell the model which tools exist, so it can correct itself
        return json.dumps({
            "error": f"Unknown tool: {name}, and available tools are: {' '.join(TOOLS.keys())}"
        })
    try:
        return func(**(args or {}))  # same as lookup_cve_details(cve_id="CVE-2024-3094")
    except Exception as e:
        # Wrong or missing arguments -> send the error back so the model can retry
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


def call_llm(messages, config, retries: int = 4):
    """Call Gemini; retry with exponential backoff on temporary errors (429 rate limit, 5xx overload)."""
    for attempt in range(retries):
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=messages,
                config=config,
            )
        except errors.APIError as e:
            if e.code not in (429, 500, 503) or attempt == retries - 1:
                raise  # permanent error, or no retries left
            wait = 5 * 2 ** attempt  # 5s, 10s, 20s
            print(f"[Retry] {e.code} - server busy, retrying in {wait}s (attempt {attempt + 2}/{retries})...")
            time.sleep(wait)


def extract_tool_and_call(tool_call) -> str:
    print(f"[LLM Requested Tool] Name: {tool_call.name} | Args: {tool_call.args}")
    tool_output = run_tool(tool_call.name, tool_call.args)
    print(f"[Local Function Output] {tool_output}")
    return tool_output


def run_react_loop(user_prompt: str) -> str:
    config = types.GenerateContentConfig(
        system_instruction=(
            "You are a cybersecurity assistant. Always use tools to verify CVE data and host inventories. "
            "Call as many tools as needed, then give a concise final answer based only on tool results."
        ),
        tools=list(TOOLS.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.0,
    )
    messages = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n=== Iteration {iteration} ===")
        response = call_llm(messages, config)

        # Stop condition: the model answered with text and requested no more tools
        if not response.function_calls:
            print(f"[Final Answer]\n{response.text}")
            return response.text

        # Keep the model's tool request in the history
        messages.append(response.candidates[0].content)

        # Execute EVERY requested tool (the model may request several in parallel)
        result_parts = []
        for call in response.function_calls:
            output = extract_tool_and_call(call)
            result_parts.append(
                types.Part.from_function_response(name=call.name, response={"result": output})
            )

        # Gemini expects function responses with role="user" (role="tool" -> 400 INVALID_ARGUMENT)
        messages.append(types.Content(role="user", parts=result_parts))

    print("[Stopped] Reached MAX_ITERATIONS without a final answer.")
    return ""


if __name__ == "__main__":
    run_react_loop(
        "Compare CVE-2024-3094 and CVE-2021-44228. "
        "Is the host db-prod-01 running any package affected by either of them?"
    )
