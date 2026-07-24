"""Extract JSON from a model response.

Instruction-tuned models routinely ignore "return ONLY JSON" and wrap the
object in ```json fences, or prefix it with "Here is the JSON:". A bare
json.loads() on that raises and takes the whole session down, so every
JSON-expecting call site goes through here instead.
"""
import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class MalformedModelJSON(ValueError):
    """The model's response contained no parseable JSON object."""


def parse_json_response(raw: str) -> dict:
    if raw is None:
        raise MalformedModelJSON("model returned no content")

    text = raw.strip()

    # 1. Clean JSON, the happy path.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Fenced code block.
    fenced = _FENCE.search(text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Widest brace-balanced span -- handles prose on either side of the object.
    start = text.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise MalformedModelJSON(f"no parseable JSON in model response: {text[:200]!r}")
