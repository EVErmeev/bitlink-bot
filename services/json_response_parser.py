"""JSON response parser with repair/retry capability."""
import json
import re
from pathlib import Path


def parse_and_validate_json(raw_text, schema, *,
                             max_repair_attempts=2,
                             debug_dir=None,
                             generate_fn=None):
    """Parse raw LLM text, validate against schema, retry on failure.
    Returns (parsed_dict, errors_list)."""
    errors = []

    for attempt in range(max_repair_attempts + 1):
        attempt_label = f"attempt_{attempt + 1}"

        if debug_dir:
            debug_dir = Path(debug_dir)
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / f"llm_{attempt_label}_raw.txt").write_text(raw_text, encoding="utf-8")

        cleaned = _extract_json(raw_text)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            error_msg = f"JSON parse error at line {e.lineno} col {e.colno}: {e.msg}"
            errors.append(error_msg)
            if debug_dir:
                (debug_dir / f"llm_{attempt_label}_parse_error.txt").write_text(error_msg, encoding="utf-8")

            if attempt < max_repair_attempts and generate_fn:
                repair_prompt = (
                    "Fix ONLY the JSON syntax. Do NOT change content.\n"
                    f"Error: {error_msg}\n"
                    "Return ONLY one JSON object, no markdown.\n"
                    f"Schema: {json.dumps(schema, ensure_ascii=False)}\n"
                    f"Original: {raw_text[:3000]}"
                )
                try:
                    raw_text = generate_fn(repair_prompt, "Fix the JSON syntax error")
                except Exception as e2:
                    errors.append(f"Repair attempt failed: {e2}")
                    break
                continue
            break

        try:
            import jsonschema
            jsonschema.validate(parsed, schema)
            return parsed, errors
        except jsonschema.ValidationError as ve:
            error_msg = f"Schema validation failed: {ve.message}"
            errors.append(error_msg)
            if debug_dir:
                (debug_dir / f"llm_{attempt_label}_schema_errors.json").write_text(
                    json.dumps({"errors": errors, "path": list(ve.absolute_path)}, indent=2),
                    encoding="utf-8")

            if attempt < max_repair_attempts and generate_fn:
                repair_prompt = (
                    "Fix the JSON to match this schema. "
                    f"Error: {ve.message} at path {list(ve.absolute_path)}.\n"
                    f"Schema: {json.dumps(schema, ensure_ascii=False)}\n"
                    f"Original: {json.dumps(parsed, ensure_ascii=False)[:2000]}"
                )
                try:
                    raw_text = generate_fn(repair_prompt, "Fix JSON schema compliance")
                except Exception:
                    break
                continue
            break

    raise RuntimeError(f"JSON invalid after {max_repair_attempts + 1} attempts: {'; '.join(errors[-3:])}")


def _extract_json(text):
    """Extract JSON from text: remove BOM, fences, find balanced braces."""
    text = text.lstrip("\ufeff").strip()

    fences = re.findall(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if len(fences) == 1:
        text = fences[0].strip()

    start = text.find('{')
    if start < 0:
        return text
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return text
