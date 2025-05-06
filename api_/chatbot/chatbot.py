from exponents.utils import call_exponents
from openai import OpenAI
import re

SYSTEM_PROMPT = (
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
            frequency_penalty=2.0,
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


def parse_function_call(response: str) -> dict:
    match = re.match(r'<functioncall>\s*(\w+)\((.*)\)', response)
    if not match:
        return None
    function_name = match.group(1)
    params_str = match.group(2)
    params = {}
    for part in params_str.split(','):
        part = part.strip()
        if not part:
            continue
        key_value = part.split('=', 1)
        if len(key_value) != 2:
            continue
        key = key_value[0].strip()
        value = key_value[1].strip()
        if value.lower() == 'unknown':
            params[key] = 'unknown'
        elif value.startswith("'") or value.startswith('"'):
            params[key] = value[1:-1]
        else:
            try:
                params[key] = int(value)
            except ValueError:
                try:
                    params[key] = float(value)
                except ValueError:
                    params[key] = value
    return {'function': function_name, 'parameters': params}


def respond(text: str, api_key: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text}
    ]
    msg = call_llm(messages, api_key)
    if not msg or not msg.content:
        return "I encountered an error processing your request."
    response_content = msg.content.strip()

    if response_content == "I cannot help with that request.":
        return response_content

    func_call = parse_function_call(response_content)
    if not func_call:
        return "I cannot help with that request."

    function_name = func_call['function']
    parameters = func_call['parameters']

    unknown_params = [k for k, v in parameters.items() if v == 'unknown']
    if unknown_params:
        return f"Please provide the following parameters: {', '.join(unknown_params)}."

    try:
        if function_name == 'computeErrorProbability':
            modulation = parameters.get('modulation', '')
            if '-' not in modulation:
                return "Modulation must be in 'M-Type' format (e.g., '4-QAM')."
            M_str, typeM = modulation.split('-', 1)
            try:
                M = int(M_str)
            except ValueError:
                return f"Invalid modulation order '{M_str}'. Must be an integer."

            quadrature_nodes = parameters.get('quadrature_nodes')
            snr = parameters.get('snr')
            rate = parameters.get('rate')

            values = call_exponents(M, typeM, snr, rate, quadrature_nodes)
            return (
                f"Results:\n"
                f"• Error probability: {values[0]:.4f}\n"
                f"• Exponent: {values[1]:.4f}\n"
                f"• Optimal rho: {values[2]:.4f}"
            )
        elif function_name == 'computeErrorExponent':
            modulation = parameters.get('modulation', '')
            if '-' not in modulation:
                return "Modulation must be in 'M-Type' format (e.g., '4-QAM')."
            M_str, typeM = modulation.split('-', 1)
            try:
                M = int(M_str)
            except ValueError:
                return f"Invalid modulation order '{M_str}'. Must be an integer."

            quadrature_nodes = parameters.get('quadrature_nodes')
            snr = parameters.get('snr')
            rate = parameters.get('rate')

            values = call_exponents(M, typeM, snr, rate, quadrature_nodes)
            return (
                f"Results:\n"
                f"• Exponent: {values[1]:.4f}\n"
                f"• Optimal rho: {values[2]:.4f}"
            )
        else:
            return "I cannot help with that request."
    except Exception as e:
        return f"An error occurred: {str(e)}"