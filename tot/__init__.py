from dataclasses import dataclass

from .agent import Agent
from .interpreter import Interpreter
from .journal import Journal
from omegaconf import OmegaConf
from rich.status import Status
from .utils.config import (
    load_task_desc,
    prep_agent_workspace,
    save_run,
    _load_cfg,
    prep_cfg,
)


@dataclass
class Solution:
    code: str
    valid_metric: float


class Experiment:
    def __init__(self, data_dir: str, goal: str, eval: str | None = None, model: str | None = None):
        """Initialize a new experiment run.

        Args:
            data_dir (str): Path to the directory containing the data files.
            goal (str): Description of the goal of the task.
            eval (str | None, optional): Optional description of the preferred way for the agent to evaluate its solutions.
            model (str | None, optional): Optional model name to override the default model configuration.
        """

        _cfg = _load_cfg(use_cli_args=False)
        _cfg.data_dir = data_dir
        _cfg.goal = goal
        _cfg.eval = eval
        self.cfg = prep_cfg(_cfg)
        
        # Override model configuration if model is provided
        if model:
            self.cfg.agent.code.model = model
            self.cfg.agent.feedback.model = model

        self.task_desc = load_task_desc(self.cfg)

        with Status("Preparing agent workspace (copying and extracting files) ..."):
            prep_agent_workspace(self.cfg)

        self.journal = Journal()
        self.agent = Agent(
            task_desc=self.task_desc,
            cfg=self.cfg,
            journal=self.journal,
        )
        self.interpreter = Interpreter(
            self.cfg.workspace_dir,
            **OmegaConf.to_container(self.cfg.exec),  # type: ignore
        )

    def run(self, steps: int) -> Solution:
        for i in range(steps):
            self.agent.step(exec_callback=self.interpreter.run)
            # 只在最后一步生成可视化，中间步骤跳过以提高性能
            is_last_step = (i == steps - 1)
            save_run(self.cfg, self.journal, generate_viz=is_last_step)
        self.interpreter.cleanup_session()

        best_node = self.journal.get_best_node(only_good=False)
        return Solution(code=best_node.code, valid_metric=best_node.metric.value)
