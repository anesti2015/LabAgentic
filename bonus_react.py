import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

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
        response = client.models.generate_content(model=MODEL, contents=messages, config=config)

        # Stop condition: the model answered with text and requested no more tools
        if not response.function_calls:
            print(f"[Final Answer]\n{response.text}")
            return response.text

        # Keep the model's tool request in the history
        messages.append(response.candidates[0].content)

        # Execute EVERY requested tool (the model may request several in parallel)
        result_parts = []
        for call in response.function_calls:
            func = TOOLS.get(call.name)
            if func is None:
                output = json.dumps({"error": f"Unknown tool {call.name}"})
            else:
                output = func(**(call.args or {}))
            print(f"[Tool] {call.name}({call.args}) -> {output}")
            result_parts.append(
                types.Part.from_function_response(name=call.name, response={"result": output})
            )

        # Gemini expects function responses with role="user"
        messages.append(types.Content(role="user", parts=result_parts))

    print("[Stopped] Reached MAX_ITERATIONS without a final answer.")
    return ""

if __name__ == "__main__":
    run_react_loop(
        "Compare CVE-2024-3094 and CVE-2021-44228. "
        "Is the host db-prod-01 running any package affected by either of them?"
    )