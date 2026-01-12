"""
Prompt template management system for TOT.

This module provides a flexible, configurable prompt management system that supports:
- YAML-based prompt templates
- Variable substitution
- Version control
- Hot reload during development
"""

from .loader import PromptLoader, get_prompt_loader

__all__ = ["PromptLoader", "get_prompt_loader"]
