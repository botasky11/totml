"""
Prompt template loader with caching and variable substitution.

This module provides a flexible prompt management system that:
- Loads prompts from YAML configuration files
- Supports variable substitution with {variable} syntax
- Provides version control for prompt templates
- Supports hot reload during development
"""

import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

import yaml

logger = logging.getLogger("tot")


class PromptLoader:
    """
    Load and manage prompt templates from YAML files.
    
    Usage:
        loader = PromptLoader()
        intro = loader.get("agent", "introduction.draft")
        guidelines = loader.get_list("agent", "guidelines.implementation", timeout="30 minutes")
    """
    
    def __init__(
        self, 
        templates_dir: Optional[Path] = None, 
        version: str = "default"
    ):
        """
        Initialize the prompt loader.
        
        Args:
            templates_dir: Directory containing template YAML files.
                          Defaults to tot/prompts/templates/
            version: Version subdirectory to use (e.g., "v1", "v2").
                    "default" uses the root templates directory.
        """
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        self.version = version
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load all YAML template files from the templates directory."""
        # Check for version-specific directory
        if self.version != "default":
            version_dir = self.templates_dir / self.version
            if version_dir.exists():
                base_dir = version_dir
            else:
                logger.warning(f"Version directory '{self.version}' not found, using default")
                base_dir = self.templates_dir
        else:
            base_dir = self.templates_dir
        
        # Load all YAML files
        for yaml_file in base_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    if content:
                        name = yaml_file.stem
                        self._cache[name] = content
                        logger.debug(f"Loaded prompt template: {name} (version: {self.version})")
            except yaml.YAMLError as e:
                logger.error(f"YAML parsing error in {yaml_file}: {e}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
        
        if not self._cache:
            logger.warning(f"No prompt templates loaded from {base_dir}")
    
    def _navigate_to_key(self, data: Dict[str, Any], key: str) -> Any:
        """
        Navigate through nested dictionary using dot notation.
        
        Args:
            data: Dictionary to navigate
            key: Dot-separated key path (e.g., "introduction.draft")
        
        Returns:
            Value at the specified path
        
        Raises:
            KeyError: If path doesn't exist
        """
        value = data
        for k in key.split('.'):
            if isinstance(value, dict):
                if k not in value:
                    raise KeyError(f"Key '{k}' not found in path '{key}'")
                value = value[k]
            else:
                raise KeyError(f"Cannot navigate further at '{k}' in path '{key}'")
        return value
    
    def _substitute_variables(
        self, 
        text: str, 
        template_vars: Dict[str, Any],
        user_vars: Dict[str, Any]
    ) -> str:
        """
        Substitute variables in text using {variable} syntax.
        
        Args:
            text: Text containing {variable} placeholders
            template_vars: Variables defined in the template
            user_vars: Variables provided by the user (override template vars)
        
        Returns:
            Text with variables substituted
        """
        # Merge variables, user vars take precedence
        all_vars = {**template_vars, **user_vars}
        
        # Find all {variable} patterns
        pattern = r'\{(\w+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in all_vars:
                return str(all_vars[var_name])
            # Return original if variable not found
            return match.group(0)
        
        return re.sub(pattern, replace_var, text)
    
    def get(
        self, 
        template_name: str, 
        key: str, 
        **variables
    ) -> str:
        """
        Get a prompt template with variable substitution.
        
        Args:
            template_name: Name of the template file (without .yaml extension)
            key: Dot-separated path to the prompt (e.g., "introduction.draft")
            **variables: Variables to substitute in the template
        
        Returns:
            Prompt string with variables substituted
        
        Raises:
            KeyError: If template or key not found
        
        Example:
            intro = loader.get("agent", "introduction.draft")
            guideline = loader.get("agent", "guidelines.implementation", timeout="30 min")
        """
        if template_name not in self._cache:
            raise KeyError(f"Template '{template_name}' not found. Available: {list(self._cache.keys())}")
        
        template_data = self._cache[template_name]
        template_vars = template_data.get('variables', {})
        
        try:
            value = self._navigate_to_key(template_data, key)
        except KeyError as e:
            raise KeyError(f"Key '{key}' not found in template '{template_name}': {e}")
        
        if isinstance(value, str):
            return self._substitute_variables(value, template_vars, variables)
        
        return value
    
    def get_list(
        self, 
        template_name: str, 
        key: str, 
        **variables
    ) -> List[str]:
        """
        Get a list of prompt items with variable substitution.
        
        Args:
            template_name: Name of the template file
            key: Dot-separated path to the list
            **variables: Variables to substitute
        
        Returns:
            List of strings with variables substituted
        
        Example:
            guidelines = loader.get_list("agent", "guidelines.implementation", timeout="30 min")
        """
        if template_name not in self._cache:
            raise KeyError(f"Template '{template_name}' not found")
        
        template_data = self._cache[template_name]
        template_vars = template_data.get('variables', {})
        
        value = self._navigate_to_key(template_data, key)
        
        if not isinstance(value, list):
            raise TypeError(f"Expected list at '{key}', got {type(value).__name__}")
        
        return [
            self._substitute_variables(item, template_vars, variables) 
            if isinstance(item, str) else item
            for item in value
        ]
    
    def get_func_spec(
        self, 
        template_name: str, 
        spec_name: str = "review"
    ) -> Dict[str, Any]:
        """
        Get function specification for LLM function calling.
        
        Args:
            template_name: Name of the template file
            spec_name: Name of the function spec (default: "review")
        
        Returns:
            Dictionary with function spec configuration
        
        Example:
            spec = loader.get_func_spec("agent", "review")
            # Returns: {"name": "submit_review", "json_schema": {...}, "description": "..."}
        """
        if template_name not in self._cache:
            raise KeyError(f"Template '{template_name}' not found")
        
        template_data = self._cache[template_name]
        func_specs = template_data.get('function_specs', {})
        
        if spec_name not in func_specs:
            raise KeyError(f"Function spec '{spec_name}' not found in '{template_name}'")
        
        return func_specs[spec_name]
    
    def get_packages(
        self, 
        template_name: str, 
        shuffle: bool = True
    ) -> List[str]:
        """
        Get list of available packages.
        
        Args:
            template_name: Name of the template file
            shuffle: Whether to shuffle the package list
        
        Returns:
            List of package names
        """
        packages = self.get_list(template_name, "environment.packages")
        if shuffle:
            packages = packages.copy()
            random.shuffle(packages)
        return packages
    
    def get_environment_prompt(
        self, 
        template_name: str, 
        shuffle_packages: bool = True
    ) -> str:
        """
        Get formatted environment information prompt.
        
        Args:
            template_name: Name of the template file
            shuffle_packages: Whether to shuffle package list
        
        Returns:
            Formatted environment prompt string
        """
        packages = self.get_packages(template_name, shuffle=shuffle_packages)
        pkg_str = ", ".join([f"`{p}`" for p in packages])
        
        template = self.get(template_name, "environment.template")
        return template.replace("{packages}", pkg_str)
    
    def get_variables(self, template_name: str) -> Dict[str, Any]:
        """
        Get all variables defined in a template.
        
        Args:
            template_name: Name of the template file
        
        Returns:
            Dictionary of template variables
        """
        if template_name not in self._cache:
            raise KeyError(f"Template '{template_name}' not found")
        
        return self._cache[template_name].get('variables', {})
    
    def list_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self._cache.keys())
    
    def reload(self) -> None:
        """
        Reload all templates from disk.
        
        Useful for hot-reload during development.
        """
        self._cache.clear()
        self._load_templates()
        logger.info(f"Reloaded {len(self._cache)} prompt templates")
    
    def get_raw(self, template_name: str) -> Dict[str, Any]:
        """
        Get raw template data without processing.
        
        Args:
            template_name: Name of the template file
        
        Returns:
            Raw dictionary from YAML file
        """
        if template_name not in self._cache:
            raise KeyError(f"Template '{template_name}' not found")
        
        return self._cache[template_name]


# =============================================================================
# Global Singleton Instance
# =============================================================================

_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader(
    version: str = "default",
    force_reload: bool = False
) -> PromptLoader:
    """
    Get or create the global prompt loader instance.
    
    Args:
        version: Version of templates to use
        force_reload: Force reload templates even if already loaded
    
    Returns:
        Global PromptLoader instance
    
    Example:
        prompts = get_prompt_loader()
        intro = prompts.get("agent", "introduction.draft")
    """
    global _prompt_loader
    
    if _prompt_loader is None or _prompt_loader.version != version or force_reload:
        _prompt_loader = PromptLoader(version=version)
    
    return _prompt_loader


def reset_prompt_loader() -> None:
    """Reset the global prompt loader (useful for testing)."""
    global _prompt_loader
    _prompt_loader = None
