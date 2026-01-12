"""
Agent module for TOT (Tree of Thought) ML experiments.

This module contains the Agent class which orchestrates the ML experiment workflow:
- Drafting initial solutions
- Improving existing solutions
- Debugging buggy solutions
- Parsing execution results
"""

import logging
import random
from typing import Any, Callable, Optional, cast

import humanize
from .backend import FunctionSpec, query
from .interpreter import ExecutionResult
from .journal import Journal, Node
from .prompts import get_prompt_loader, PromptLoader
from .utils import data_preview
from .utils.config import Config
from .utils.metric import MetricValue, WorstMetricValue
from .utils.response import extract_code, extract_text_up_to_code, wrap_code

logger = logging.getLogger("tot")


ExecCallbackType = Callable[[str, bool], ExecutionResult]


def _create_review_func_spec(prompts: PromptLoader) -> FunctionSpec:
    """
    Create the review function specification from prompt templates.
    
    Args:
        prompts: PromptLoader instance
    
    Returns:
        FunctionSpec for the review function
    """
    spec_config = prompts.get_func_spec("agent", "review")
    return FunctionSpec(
        name=spec_config["name"],
        json_schema=spec_config["json_schema"],
        description=spec_config["description"],
    )


class Agent:
    """
    Agent that manages the ML experiment workflow.
    
    The agent is responsible for:
    - Selecting which node to work on (search policy)
    - Generating new solution drafts
    - Improving existing solutions
    - Debugging buggy solutions
    - Parsing and evaluating execution results
    
    Attributes:
        task_desc: Description of the ML task
        cfg: Global configuration
        acfg: Agent-specific configuration
        journal: Journal containing all experiment nodes
        data_preview: Preview of the input data
        prompts: Prompt template loader
    """
    
    def __init__(
        self,
        task_desc: str,
        cfg: Config,
        journal: Journal,
        prompt_version: str = "default",
    ):
        """
        Initialize the Agent.
        
        Args:
            task_desc: Description of the ML task to solve
            cfg: Global configuration object
            journal: Journal to store experiment nodes
            prompt_version: Version of prompt templates to use (default: "default")
        """
        super().__init__()
        self.task_desc = task_desc
        self.cfg = cfg
        self.acfg = cfg.agent
        self.journal = journal
        self.data_preview: str | None = None
        
        # Initialize prompt loader
        self.prompts = get_prompt_loader(version=prompt_version)
        
        # Create review function spec from templates
        self._review_func_spec = _create_review_func_spec(self.prompts)

    def search_policy(self) -> Node | None:
        """
        Select a node to work on based on the search policy.
        
        Returns:
            Node to work on, or None to draft a new solution
        """
        search_cfg = self.acfg.search

        # Initial drafting - ensure minimum number of drafts
        if len(self.journal.draft_nodes) < search_cfg.num_drafts:
            logger.debug("[search policy] drafting new node (not enough drafts)")
            return None

        # Debugging - with some probability, try to fix buggy nodes
        if random.random() < search_cfg.debug_prob:
            # nodes that are buggy + leaf nodes + debug depth < max debug depth
            debuggable_nodes = [
                n
                for n in self.journal.buggy_nodes
                if (n.is_leaf and n.debug_depth <= search_cfg.max_debug_depth)
            ]
            if debuggable_nodes:
                logger.debug("[search policy] debugging")
                return random.choice(debuggable_nodes)
            logger.debug("[search policy] not debugging by chance")

        # Back to drafting if no good nodes to improve
        good_nodes = self.journal.good_nodes
        if not good_nodes:
            logger.debug("[search policy] drafting new node (no good nodes)")
            return None

        # Greedy - select the best node to improve
        greedy_node = self.journal.get_best_node()
        logger.debug("[search policy] greedy node selected")
        return greedy_node

    @property
    def _prompt_environment(self) -> dict:
        """Get environment information prompt with shuffled package list."""
        env_text = self.prompts.get_environment_prompt("agent", shuffle_packages=True)
        return {"Installed Packages": env_text}

    @property
    def _prompt_impl_guideline(self) -> dict:
        """Get implementation guidelines with dynamic variables."""
        # Get base guidelines with timeout substitution
        timeout_str = humanize.naturaldelta(self.cfg.exec.timeout)
        guidelines = self.prompts.get_list(
            "agent", 
            "guidelines.implementation",
            timeout=timeout_str
        )
        
        # Add optional guidelines based on configuration
        if self.acfg.expose_prediction:
            prediction_guideline = self.prompts.get(
                "agent",
                "guidelines.implementation_optional.expose_prediction"
            )
            guidelines.append(prediction_guideline)

        if self.acfg.k_fold_validation > 1:
            k_fold_guideline = self.prompts.get(
                "agent",
                "guidelines.implementation_optional.k_fold_validation",
                k_fold=self.acfg.k_fold_validation
            )
            guidelines.append(k_fold_guideline)

        return {"Implementation guideline": guidelines}

    @property
    def _prompt_resp_fmt(self) -> dict:
        """Get response format instructions."""
        return {"Response format": self.prompts.get("agent", "response_format")}

    def plan_and_code_query(self, prompt: Any, retries: int = 3) -> tuple[str, str]:
        """
        Generate a natural language plan + code in the same LLM call.
        
        Args:
            prompt: The prompt to send to the LLM
            retries: Number of retries on failure
        
        Returns:
            Tuple of (plan_text, code_text)
        """
        completion_text = None
        for _ in range(retries):
            completion_text = query(
                system_message=prompt,
                user_message=None,
                model=self.acfg.code.model,
                temperature=self.acfg.code.temp,
            )

            code = extract_code(completion_text)
            nl_text = extract_text_up_to_code(completion_text)

            if code and nl_text:
                # Merge all code blocks into a single string
                return nl_text, code

            print("Plan + code extraction failed, retrying...")
        
        print("Final plan + code extraction attempt failed, giving up...")
        return "", completion_text  # type: ignore

    def _draft(self) -> Node:
        """
        Generate a new solution draft.
        
        Returns:
            New Node with the drafted solution
        """
        prompt: Any = {
            "Introduction": self.prompts.get("agent", "introduction.draft"),
            "Task description": self.task_desc,
            "Memory": self.journal.generate_summary(),
            "Instructions": {},
        }
        
        prompt["Instructions"] |= self._prompt_resp_fmt
        prompt["Instructions"] |= {
            "Solution sketch guideline": self.prompts.get_list("agent", "guidelines.solution_sketch")
        }
        prompt["Instructions"] |= self._prompt_impl_guideline
        prompt["Instructions"] |= self._prompt_environment

        if self.acfg.data_preview:
            prompt["Data Overview"] = self.data_preview

        plan, code = self.plan_and_code_query(prompt)
        return Node(plan=plan, code=code)

    def _improve(self, parent_node: Node) -> Node:
        """
        Generate an improved solution based on a parent node.
        
        Args:
            parent_node: The node to improve upon
        
        Returns:
            New Node with the improved solution
        """
        prompt: Any = {
            "Introduction": self.prompts.get("agent", "introduction.improve"),
            "Task description": self.task_desc,
            "Memory": self.journal.generate_summary(),
            "Instructions": {},
        }
        prompt["Previous solution"] = {
            "Code": wrap_code(parent_node.code),
        }

        prompt["Instructions"] |= self._prompt_resp_fmt
        prompt["Instructions"] |= {
            "Solution improvement sketch guideline": self.prompts.get_list(
                "agent", "guidelines.improvement"
            )
        }
        prompt["Instructions"] |= self._prompt_impl_guideline

        plan, code = self.plan_and_code_query(prompt)
        return Node(
            plan=plan,
            code=code,
            parent=parent_node,
        )

    def _debug(self, parent_node: Node) -> Node:
        """
        Generate a debugged solution based on a buggy parent node.
        
        Args:
            parent_node: The buggy node to debug
        
        Returns:
            New Node with the debugged solution
        """
        prompt: Any = {
            "Introduction": self.prompts.get("agent", "introduction.debug"),
            "Task description": self.task_desc,
            "Previous (buggy) implementation": wrap_code(parent_node.code),
            "Execution output": wrap_code(parent_node.term_out, lang=""),
            "Instructions": {},
        }
        
        prompt["Instructions"] |= self._prompt_resp_fmt
        prompt["Instructions"] |= {
            "Bugfix improvement sketch guideline": self.prompts.get_list(
                "agent", "guidelines.bugfix"
            )
        }
        prompt["Instructions"] |= self._prompt_impl_guideline

        if self.acfg.data_preview:
            prompt["Data Overview"] = self.data_preview

        plan, code = self.plan_and_code_query(prompt)
        return Node(plan=plan, code=code, parent=parent_node)

    def update_data_preview(self) -> None:
        """Update the data preview from the workspace directory."""
        self.data_preview = data_preview.generate(self.cfg.workspace_dir)

    def step(self, exec_callback: ExecCallbackType) -> None:
        """
        Execute one step of the agent workflow.
        
        This method:
        1. Updates data preview if needed
        2. Selects a node based on search policy
        3. Generates new code (draft, improve, or debug)
        4. Executes the code and parses results
        5. Appends the result to the journal
        
        Args:
            exec_callback: Callback function to execute the generated code
        """
        if not self.journal.nodes or self.data_preview is None:
            self.update_data_preview()

        parent_node = self.search_policy()
        logger.debug(f"Agent is generating code, parent node type: {type(parent_node)}")

        if parent_node is None:
            result_node = self._draft()
        elif parent_node.is_buggy:
            result_node = self._debug(parent_node)
        else:
            result_node = self._improve(parent_node)

        self.parse_exec_result(
            node=result_node,
            exec_result=exec_callback(result_node.code, True),
        )
        self.journal.append(result_node)

    def parse_exec_result(self, node: Node, exec_result: ExecutionResult) -> None:
        """
        Parse and evaluate the execution result of a node.
        
        Args:
            node: The node whose code was executed
            exec_result: The execution result to parse
        """
        logger.info(f"Agent is parsing execution results for node {node.id}")

        node.absorb_exec_result(exec_result)

        prompt = {
            "Introduction": self.prompts.get("agent", "introduction.review"),
            "Task description": self.task_desc,
            "Implementation": wrap_code(node.code),
            "Execution output": wrap_code(node.term_out, lang=""),
        }

        response = cast(
            dict,
            query(
                system_message=prompt,
                user_message=None,
                func_spec=self._review_func_spec,
                model=self.acfg.feedback.model,
                temperature=self.acfg.feedback.temp,
            ),
        )

        # Check if response is a valid dict
        if not isinstance(response, dict):
            logger.warning(
                f"OpenAI API returned invalid response type: {type(response).__name__}. "
                f"Expected dict, got: {response}"
            )
            node.analysis = "Error: Invalid API response received. Unable to parse execution results."
            node.is_buggy = True
            node.metric = WorstMetricValue()
            return

        # If the metric isn't a float, set it to None
        if not isinstance(response.get("metric"), float):
            response["metric"] = None

        node.analysis = response.get("summary", "No summary provided")
        node.is_buggy = (
            response.get("is_bug", False)
            or node.exc_type is not None
            or response["metric"] is None
        )

        if node.is_buggy:
            node.metric = WorstMetricValue()
        else:
            node.metric = MetricValue(
                response["metric"], 
                maximize=not response.get("lower_is_better", True)
            )


# =============================================================================
# Backward Compatibility
# =============================================================================
# Keep the old review_func_spec for backward compatibility
# This will be lazily initialized when first accessed

_review_func_spec: Optional[FunctionSpec] = None

def get_review_func_spec() -> FunctionSpec:
    """
    Get the review function specification.
    
    This function is provided for backward compatibility.
    New code should use Agent._review_func_spec instead.
    """
    global _review_func_spec
    if _review_func_spec is None:
        prompts = get_prompt_loader()
        _review_func_spec = _create_review_func_spec(prompts)
    return _review_func_spec


# Alias for backward compatibility
review_func_spec = property(lambda self: get_review_func_spec())
