from . import backend_anthropic, backend_openai, backend_openrouter, backend_gemini, backend_litellm
from .utils import FunctionSpec, OutputType, PromptType, compile_prompt_to_md
import re
import logging
import os

logger = logging.getLogger("tot")


def determine_provider(model: str) -> tuple[str, dict[str, str]]:
    api_base = None
    api_key = None
    provider = None
    formatted_model = None
    
    # Check if model matches OpenAI patterns first
    # LiteLLM 中的 model 参数需要为provider/model 格式，例如："qwen/qwen-max" 格式
    if re.match(r"^(gpt-.*|o\d+(-.*)?|codex-mini-latest)$", model):
        api_base = os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("OPENAI_API_KEY")
        provider = "openai"
        formatted_model = f"{provider}/{model}"
    elif model.startswith("claude-"):
        api_base = os.getenv("ANTHROPIC_BASE_URL")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        provider = "anthropic"
        formatted_model = f"{provider}/{model}"
    elif model.startswith("gemini-"):
        api_base = os.getenv("GEMINI_BASE_URL")
        api_key = os.getenv("GEMINI_API_KEY")
        provider = "gemini"
        formatted_model = f"{provider}/{model}"
    elif model.startswith("qwen"):
        api_base = os.getenv("DASHSCOPE_BASE_URL")
        api_key = os.getenv("DASHSCOPE_API_KEY")
        provider = "dashscope"
        formatted_model = f"{provider}/{model}"
    elif model.startswith("openrouter"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        api_base = os.getenv("OPENROUTER_BASE_URL")
        provider = "openai"
        formatted_model = f"{provider}/{model}"
    
    provider_kwargs = {
        "model": formatted_model,
        "api_key": api_key,
        "api_base": api_base,
    }
    
    return provider, provider_kwargs


provider_to_query_func = {
    "openai": backend_litellm.query,
    "anthropic": backend_litellm.query,
    "openrouter": backend_litellm.query,
    "gemini": backend_litellm.query,
    "dashscope": backend_litellm.query,
}


def query(
    system_message: PromptType | None,
    user_message: PromptType | None,
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    func_spec: FunctionSpec | None = None,
    **model_kwargs,
) -> OutputType:
    """
    General LLM query for various backends with a single system and user message.
    Supports function calling for some backends.

    Args:
        system_message (PromptType | None): Uncompiled system message (will generate a message following the OpenAI/Anthropic format)
        user_message (PromptType | None): Uncompiled user message (will generate a message following the OpenAI/Anthropic format)
        model (str): string identifier for the model to use (e.g. "gpt-4-turbo")
        temperature (float | None, optional): Temperature to sample at. Defaults to the model-specific default.
        max_tokens (int | None, optional): Maximum number of tokens to generate. Defaults to the model-specific max tokens.
        func_spec (FunctionSpec | None, optional): Optional FunctionSpec object defining a function call. If given, the return value will be a dict.

    Returns:
        OutputType: A string completion if func_spec is None, otherwise a dict with the function call details.
    """
    provider, provider_kwargs = determine_provider(model)

    if provider:
        model_kwargs = model_kwargs | provider_kwargs | {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    else:
        logger.error(f"Unknown model: {model}")
        raise ValueError(f"Unknown model: {model}")
    
    #Anthropic 的 Messages API 强制要求至少有 1 条非 system 消息（user/assistant）
    if provider == "anthropic":
        if not user_message:
            user_message = "Please continue."

    query_func = provider_to_query_func[provider]
    output, req_time, in_tok_count, out_tok_count, info = query_func(
        system_message=compile_prompt_to_md(system_message) if system_message else None,
        user_message=compile_prompt_to_md(user_message) if user_message else None,
        func_spec=func_spec,
        **model_kwargs,
    )

    return output
