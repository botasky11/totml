import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aide import Experiment as AIDEExperiment
from backend.models.experiment import Experiment, ExperimentNode
from backend.schemas import ExperimentCreate, ExperimentUpdate, ExperimentStatus
from backend.core.config import settings

logger = logging.getLogger(__name__)


class ExperimentService:
    """Service for managing AIDE ML experiments"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_experiment(
        self,
        experiment_data: ExperimentCreate,
        data_dir: str
    ) -> Experiment:
        """Create a new experiment"""
        experiment = Experiment(
            name=experiment_data.name,
            description=experiment_data.description,
            goal=experiment_data.goal,
            eval_metric=experiment_data.eval_metric,
            num_steps=experiment_data.num_steps,
            model_name=experiment_data.model_name,
            data_dir=data_dir,
            status=ExperimentStatus.PENDING,
            current_step=0,
            progress=0.0,
        )
        
        self.db.add(experiment)
        await self.db.commit()
        await self.db.refresh(experiment)
        
        return experiment
    
    async def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID"""
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        return result.scalar_one_or_none()
    
    async def list_experiments(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Experiment]:
        """List all experiments"""
        result = await self.db.execute(
            select(Experiment)
            .order_by(Experiment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_experiment(
        self,
        experiment_id: str,
        update_data: ExperimentUpdate
    ) -> Optional[Experiment]:
        """Update experiment"""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(experiment, key, value)
        
        experiment.updated_at = datetime.now()
        
        if update_data.status == ExperimentStatus.COMPLETED:
            experiment.completed_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(experiment)
        
        return experiment
    
    async def delete_experiment(self, experiment_id: str) -> bool:
        """Delete experiment"""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return False
        
        await self.db.delete(experiment)
        await self.db.commit()
        
        return True
    
    async def create_node(
        self,
        experiment_id: str,
        step: int,
        code: str,
        plan: Optional[str] = None,
        parent_id: Optional[str] = None,
        metric_value: Optional[float] = None,
        is_buggy: bool = False,
        term_out: Optional[str] = None,
        analysis: Optional[str] = None,
    ) -> ExperimentNode:
        """Create a new experiment node"""
        node = ExperimentNode(
            experiment_id=experiment_id,
            step=step,
            parent_id=parent_id,
            plan=plan,
            code=code,
            metric_value=metric_value,
            is_buggy=is_buggy,
            term_out=term_out,
            analysis=analysis,
        )
        
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        
        return node
    
    async def get_experiment_nodes(
        self,
        experiment_id: str
    ) -> List[ExperimentNode]:
        """Get all nodes for an experiment"""
        result = await self.db.execute(
            select(ExperimentNode)
            .where(ExperimentNode.experiment_id == experiment_id)
            .order_by(ExperimentNode.step)
        )
        return list(result.scalars().all())
    
    async def run_experiment_async(
        self,
        experiment_id: str,
        websocket_callback=None
    ):
        """Run AIDE experiment asynchronously"""
        try:
            logger.info(f"[EXP_SERVICE] Starting experiment {experiment_id}")
            logger.info(f"[EXP_SERVICE] WebSocket callback available: {websocket_callback is not None}")

            experiment = await self.get_experiment(experiment_id)
            if not experiment:
                raise ValueError(f"Experiment {experiment_id} not found")

            logger.info(f"[EXP_SERVICE] Found experiment: {experiment.name}, current status: {experiment.status}")

            # Update status to running
            await self.update_experiment(
                experiment_id,
                ExperimentUpdate(status=ExperimentStatus.RUNNING)
            )
            logger.info(f"[EXP_SERVICE] Updated experiment status to RUNNING")

            # Send initial status
            if websocket_callback:
                logger.info(f"[EXP_SERVICE] Sending initial status_update via WebSocket")
                await websocket_callback({
                    "type": "status_update",
                    "data": {
                        "experiment_id": experiment_id,
                        "status": "running",
                        "step": 0,
                        "progress": 0.0
                    }
                })
                logger.info(f"[EXP_SERVICE] Initial status_update sent successfully")
            else:
                logger.warning(f"[EXP_SERVICE] Send initial status Failed: No active WebSocket connection for experiment {experiment_id}")
            
            # Initialize AIDE experiment
            aide_exp = AIDEExperiment(
                data_dir=experiment.data_dir,
                goal=experiment.goal,
                eval=experiment.eval_metric,
            )
            
            # Run steps - manually control each step without intermediate visualizations
            from aide.utils.config import save_run
            logger.info(f"[EXP_SERVICE] Starting {experiment.num_steps} steps execution")

            for step in range(experiment.num_steps):
                logger.info(f"[EXP_SERVICE] Executing step {step + 1}/{experiment.num_steps}")

                # Execute one agent step WITHOUT generating visualization
                aide_exp.agent.step(exec_callback=aide_exp.interpreter.run)
                # Save the run state without generating expensive visualization
                save_run(aide_exp.cfg, aide_exp.journal, generate_viz=False)

                # Update progress
                progress = (step + 1) / experiment.num_steps
                logger.info(f"[EXP_SERVICE] Step {step + 1} completed, progress: {progress * 100:.1f}%")

                await self.update_experiment(
                    experiment_id,
                    ExperimentUpdate(
                        current_step=step + 1,
                        progress=progress
                    )
                )
                logger.info(f"[EXP_SERVICE] Database updated with progress")

                # Send progress update
                if websocket_callback:
                    logger.info(f"[EXP_SERVICE] Sending progress update via WebSocket for step {step + 1}")
                    await websocket_callback({
                        "type": "status_update",
                        "data": {
                            "experiment_id": experiment_id,
                            "status": "running",
                            "step": step + 1,
                            "progress": progress,
                            "total_steps": experiment.num_steps
                        }
                    })
                    logger.info(f"[EXP_SERVICE] Progress update sent successfully for step {step + 1}")
                else:
                    logger.warning(f"[EXP_SERVICE] Send progress update Failed: No active WebSocket connection for experiment {experiment_id}")
                
                # Save nodes from journal
                for node in aide_exp.journal.nodes:
                    await self.create_node(
                        experiment_id=experiment_id,
                        step=node.step,
                        code=str(node.code),
                        plan=node.plan,
                        metric_value=float(node.metric.value) if (node.metric and node.metric.value is not None) else None,
                        is_buggy=node.is_buggy,
                        term_out=node.term_out,
                        analysis=node.analysis,
                    )
            
            # Cleanup interpreter session
            aide_exp.interpreter.cleanup_session()
            
            # Generate final tree visualization ONLY ONCE at the end
            try:
                save_run(aide_exp.cfg, aide_exp.journal, generate_viz=True)
                logger.info(f"Generated final tree visualization for experiment {experiment_id}")
            except Exception as viz_error:
                logger.warning(f"Failed to generate tree visualization: {viz_error}")
            
            # Get best solution
            # 首先尝试获取非buggy的最佳节点
            best_node = aide_exp.journal.get_best_node(only_good=True)
            
            # 如果没有非buggy节点，获取所有节点中的第一个（即使是buggy的）
            if not best_node and aide_exp.journal.nodes:
                logger.info(f"[EXP_SERVICE] No good nodes found, using first node from all nodes")
                best_node = aide_exp.journal.nodes[0]
            
            best_solution_code = str(best_node.code) if best_node else None
            best_metric_value = float(best_node.metric.value) if (best_node and best_node.metric and best_node.metric.value is not None) else None
            
            logger.info(f"[EXP_SERVICE] Best node selected: code_length={len(best_solution_code) if best_solution_code else 0}, metric={best_metric_value}")
            
            # Collect journal data
            journal_data = [
                {
                    "step": node.step,
                    "code": str(node.code),
                    "metric": float(node.metric.value) if (node.metric and node.metric.value is not None) else None,
                    "is_buggy": node.is_buggy,
                }
                for node in aide_exp.journal.nodes
            ]
            
            # Update experiment with results
            await self.update_experiment(
                experiment_id,
                ExperimentUpdate(
                    status=ExperimentStatus.COMPLETED,
                    best_solution_code=best_solution_code,
                    best_metric_value=best_metric_value,
                    journal_data=journal_data,
                    progress=1.0
                )
            )
            
            # Send completion message
            logger.info(f"[EXP_SERVICE] Experiment completed, sending completion message")
            if websocket_callback:
                await websocket_callback({
                    "type": "complete",
                    "data": {
                        "experiment_id": experiment_id,
                        "status": "completed",
                        "best_metric_value": best_metric_value,
                        "best_solution_code": best_solution_code
                    }
                })
                logger.info(f"[EXP_SERVICE] Completion message sent successfully")
            else:
                logger.warning(f"[EXP_SERVICE] Send completion message Failed: No active WebSocket connection for experiment {experiment_id}")
            
        except Exception as e:
            logger.error(f"[EXP_SERVICE] Error running experiment {experiment_id}: {str(e)}", exc_info=True)

            # Update experiment status to failed
            await self.update_experiment(
                experiment_id,
                ExperimentUpdate(
                    status=ExperimentStatus.FAILED,
                    error_message=str(e)
                )
            )
            logger.info(f"[EXP_SERVICE] Updated experiment status to FAILED")

            # Send error message
            if websocket_callback:
                logger.info(f"[EXP_SERVICE] Sending error message via WebSocket")
                await websocket_callback({
                    "type": "error",
                    "data": {
                        "experiment_id": experiment_id,
                        "error": str(e)
                    }
                })
                logger.info(f"[EXP_SERVICE] Error message sent successfully")
            else:
                logger.warning(f"[EXP_SERVICE] Send error message Failed: No active WebSocket connection for experiment {experiment_id}")
