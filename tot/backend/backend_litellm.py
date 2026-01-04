"""Backend for LiteLLM."""

import json
import logging
import time
import os
import re

import litellm
from .utils import FunctionSpec, OutputType, opt_messages_to_list, backoff_create
from funcy import notnone, select_values

logger = logging.getLogger("tot")

LITELLM_TIMEOUT_EXCEPTIONS = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.Timeout,
    litellm.exceptions.APIConnectionError,
    litellm.exceptions.ServiceUnavailableError,
)


def _fix_malformed_json(json_str: str) -> str:
    """
    Attempt to fix common JSON malformation issues from LLM output.
    
    Common issues:
    - Empty values like "metric": , (should be "metric": null)
    - Trailing commas
    - Missing quotes around keys
    """
    # Fix empty values: "key": , -> "key": null,
    # Pattern matches: "key": followed by comma or closing brace
    fixed = re.sub(r':\s*,', ': null,', json_str)
    fixed = re.sub(r':\s*}', ': null}', fixed)
    
    # Fix trailing commas before closing braces/brackets
    fixed = re.sub(r',\s*}', '}', fixed)
    fixed = re.sub(r',\s*]', ']', fixed)
    
    return fixed


def query(
    system_message: str | None,
    user_message: str | None,
    func_spec: FunctionSpec | None = None,
    **model_kwargs,
) -> tuple[OutputType, float, int, int, dict]:
    """
    Query via LiteLLM.
    """
    messages = opt_messages_to_list(system_message, user_message)

    filtered_kwargs: dict = select_values(notnone, model_kwargs)
    
    # Handle max_tokens vs max_completion_tokens (liteLLM unification)
    if "max_tokens" in filtered_kwargs:
        filtered_kwargs["max_tokens"] = filtered_kwargs["max_tokens"]

    # Convert tools
    if func_spec is not None:
        filtered_kwargs["tools"] = [func_spec.as_openai_tool_dict]
        filtered_kwargs["tool_choice"] = func_spec.openai_tool_choice_dict

    logger.info(f"LiteLLM request: system={system_message}, user={user_message}")

    t0 = time.time()

    def _completion_wrapper(**kwargs):
        # drop_params=True allows LiteLLM to ignore unsupported params for specific providers
        return litellm.completion(drop_params=True, **kwargs)

    try:
        response = backoff_create(
            _completion_wrapper,
            tuple(LITELLM_TIMEOUT_EXCEPTIONS),
            messages=messages,
            **filtered_kwargs,
        )
    except Exception as e:
        # Check for function calling not supported error and retry without tools
        if "does not support function calling" in str(e) or "does not support tools" in str(e):
             logger.warning("Model does not support function calling, retrying without tools.")
             filtered_kwargs.pop("tools", None)
             filtered_kwargs.pop("tool_choice", None)
             response = backoff_create(
                _completion_wrapper,
                tuple(LITELLM_TIMEOUT_EXCEPTIONS),
                messages=messages,
                **filtered_kwargs,
            )
        else:
            raise e

    req_time = time.time() - t0

    # Parse output
    choices = getattr(response, "choices", [])
    if not choices:
        logger.error("LiteLLM response has no choices")
        return "", req_time, 0, 0, {}

    message = choices[0].message

    # Check for tool definitions
    output = message.content or ""
    if hasattr(message, "tool_calls") and message.tool_calls and func_spec is not None:
        tool_call = message.tool_calls[0]
        # Check if function name matches or just take the first one?
        # Robustness: try to parse if present
        if tool_call.function.name == func_spec.name:
            try:
                output = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as ex:
                # Try to fix common JSON issues from LLM output
                logger.warning(f"Error decoding function args, attempting to fix: {tool_call.function.arguments}")
                fixed_args = _fix_malformed_json(tool_call.function.arguments)
                try:
                    output = json.loads(fixed_args)
                    logger.info(f"Successfully fixed malformed JSON")
                except json.JSONDecodeError:
                    logger.error(f"Failed to fix malformed JSON: {tool_call.function.arguments}")
                    raise ex
        else:
             logger.warning(f"Function mismatch: {tool_call.function.name} != {func_spec.name}")

    # Usage
    usage = getattr(response, "usage", None)
    if usage:
        in_tokens = usage.prompt_tokens
        out_tokens = usage.completion_tokens
    else:
        in_tokens = 0
        out_tokens = 0

    info = {
        "model": getattr(response, "model", "unknown"),
        "id": getattr(response, "id", None),
        "created": getattr(response, "created", None),
    }

    logger.info(
        f"LiteLLM call completed - {getattr(response, 'model', 'unknown')} - {req_time:.2f}s - {in_tokens + out_tokens} tokens (in: {in_tokens}, out: {out_tokens})"
    )
    logger.info(f"LiteLLM response: {output}")

    return output, req_time, in_tokens, out_tokens, info
