import json
from openai import OpenAI

# Define tools for function-calling via OpenRouter
TOOLS = [
    {
        "name": "computeErrorProbability",
        "description": "Calculates the error probability.",
        "parameters": {
            "type": "object",
            "properties": {
                "modulation": {"type": "string"},
                "quadrature_nodes": {"type": "integer"},
                "snr": {"type": "number"},
                "rate": {"type": "number"},
                "n": {
                    "oneOf": [
                            {"type": "integer"},
                        {"type": "string"}
                    ]
                }
            },
            "required": ["modulation", "quadrature_nodes", "snr", "rate", "n"]
        }
    },
    {
        "name": "computeErrorExponent",
        "description": "Calculates the error exponent (reliability function).",
        "parameters": {
            "type": "object",
            "properties": {
                "modulation": {"type": "string"},
                "quadrature_nodes": {"type": "integer"},
                "snr": {"type": "number"},
                "rate": {"type": "number"}
            },
            "required": ["modulation", "quadrature_nodes", "snr", "rate"]
        }
    }
]

# Local implementations of tools
def computeErrorProbability(modulation, quadrature_nodes, snr, rate, n):
    # Replace with your actual calculation logic
    return {"error_probability": f"Simulated P_e for {modulation} with SNR={snr}, R={rate}, n={n}"}

def computeErrorExponent(modulation, quadrature_nodes, snr, rate):
    # Replace with your actual calculation logic
    return {"error_exponent": f"Simulated E_r for {modulation} with SNR={snr}, R={rate}"}

FUNCTION_DISPATCH = {
    "computeErrorProbability": computeErrorProbability,
    "computeErrorExponent": computeErrorExponent,
}

# Wrapper to call OpenRouter via OpenAI-compatible API
def call_llm(messages, api_key, model="mistralai/mistral-7b-instruct:free"):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            frequency_penalty=2.0,  # Penalize verbose responses
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",
                "X-Title": "<YOUR_SITE_NAME>"
            }
        )
        if not resp or not resp.choices:
            raise Exception("No response from the model")
        return resp.choices[0].message
    except Exception as e:
        print(f"Error calling the model: {str(e)}")
        return None

# Interactive REPL loop
def chat_loop(api_key):
    system_prompt = (
        "You are a specialized assistant for transmission-system calculations. "
        "Your sole responsibility is to determine when to call one of two calculation tools or to decline.\n\n"
        "**Behavior Rules:**\n\n"
        "1. **Only output:**\n\n"
        "   - A single function call in the precise format:\n\n"
        "     `<functioncall> computeErrorProbability(modulation='...', quadrature_nodes=..., snr=..., rate=..., n=...)`\n\n"
        "     or\n\n"
        "     `<functioncall> computeErrorExponent(modulation='...', quadrature_nodes=..., snr=..., rate=...)`\n\n"
        "   - Or exactly: `I cannot help with that request.`\n\n"
        "2. **When to call a tool:**\n\n"
        "   - If the user's question explicitly requests error probability or error exponent calculations.\n\n"
        "   - Extract all required parameters (modulation, quadrature_nodes, snr, rate, and n if provided).\n\n"
        "   - For any missing parameter, substitute the literal string `'unknown'`.\n\n"
        "3. **When not to call:**\n\n"
        "   - If the request is unrelated to these tools, ambiguous, or lacks required fields.\n\n"
        "4. **No extra text:**\n\n"
        "   - Do not include explanations, clarifications, or multiple calls.\n\n"
        "**Examples:**\n\n"
        "- User: 'Hello'\n\n"
        "  Output: `I cannot help with that request.`\n\n"
        "- User: 'Compute error probability for 2-PAM with SNR 3'\n\n"
        "  Output: `<functioncall> computeErrorProbability(modulation='2-PAM', quadrature_nodes='unknown', snr=3, rate='unknown', n='unknown')`"
    )

    messages = [{"role": "system", "content": system_prompt}]

    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})
        msg = call_llm(messages, api_key)
        print(msg.content)
        messages.append({"role": "assistant", "content": msg.content})

if __name__ == "__main__":
    API_KEY = "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"
    chat_loop(API_KEY)
