"""
FeatureAnalysisService - 特征分析服务

负责在实验完成后生成特征分析报告：
1. 从 best_node 提取模型代码和预测结果
2. 剔除 buggy nodes，只分析成功的节点
3. 生成完整的特征分析报告并存储
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.experiment import Experiment, ExperimentNode, FeatureAnalysisReport
from backend.schemas import ExperimentStatus

# 导入特征分析模块
from tot.analysis.data_profiler import DataProfiler, DataProfileResult
from tot.analysis.feature_importance import FeatureImportance, FeatureImportanceReport
from tot.analysis.feature_stability import FeatureStability, FeatureStabilityReport
from tot.analysis.model_stability import ModelStability, ModelStabilityResult
from tot.analysis.model_evaluator import ModelEvaluator, ModelEvaluationReport
from tot.analysis.report_generator import ReportGenerator, AnalysisReport

logger = logging.getLogger(__name__)


class FeatureAnalysisService:
    """特征分析服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_report_by_experiment(
        self, 
        experiment_id: str
    ) -> Optional[FeatureAnalysisReport]:
        """根据实验ID获取分析报告"""
        result = await self.db.execute(
            select(FeatureAnalysisReport)
            .where(FeatureAnalysisReport.experiment_id == experiment_id)
        )
        return result.scalar_one_or_none()
    
    async def create_report(
        self,
        experiment_id: str,
        best_node_id: Optional[str] = None,
        data_profile: Optional[Dict] = None,
        feature_importance: Optional[Dict] = None,
        feature_stability: Optional[Dict] = None,
        model_stability: Optional[Dict] = None,
        model_evaluation: Optional[Dict] = None,
        feature_statistics: Optional[List[Dict]] = None,
        full_report_md: Optional[str] = None,
        analysis_config: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> FeatureAnalysisReport:
        """创建特征分析报告"""
        report = FeatureAnalysisReport(
            experiment_id=experiment_id,
            best_node_id=best_node_id,
            data_profile=data_profile,
            feature_importance=feature_importance,
            feature_stability=feature_stability,
            model_stability=model_stability,
            model_evaluation=model_evaluation,
            feature_statistics=feature_statistics,
            full_report_md=full_report_md,
            analysis_config=analysis_config,
            error_message=error_message
        )
        
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        return report
    
    async def update_report(
        self,
        report_id: str,
        **kwargs
    ) -> Optional[FeatureAnalysisReport]:
        """更新特征分析报告"""
        result = await self.db.execute(
            select(FeatureAnalysisReport)
            .where(FeatureAnalysisReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        
        if not report:
            return None
        
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)
        
        report.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(report)
        
        return report
    
    async def delete_report(self, experiment_id: str) -> bool:
        """删除特征分析报告"""
        report = await self.get_report_by_experiment(experiment_id)
        if not report:
            return False
        
        await self.db.delete(report)
        await self.db.commit()
        return True
    
    async def generate_analysis_report(
        self,
        experiment_id: str,
        best_node_id: Optional[str] = None,
        label_column: str = 'default_flag',
        score_column: str = 'score',
        dataset_column: Optional[str] = 'dataset',
        date_column: Optional[str] = 'dt'
    ) -> FeatureAnalysisReport:
        """
        生成特征分析报告
        
        核心逻辑：
        1. 获取实验信息和数据目录
        2. 加载训练数据
        3. 剔除 buggy nodes，找到 best_node
        4. 执行数据分析（如果有分数数据则进行模型分析）
        5. 生成并保存报告
        
        Args:
            experiment_id: 实验ID
            best_node_id: 最佳节点ID（可选，如果不提供则自动选择）
            label_column: 标签列名
            score_column: 分数列名
            dataset_column: 数据集划分列名
            date_column: 日期列名
            
        Returns:
            FeatureAnalysisReport 对象
        """
        logger.info(f"[FEATURE_ANALYSIS] Starting analysis for experiment {experiment_id}")
        
        # 检查是否已存在报告
        existing_report = await self.get_report_by_experiment(experiment_id)
        if existing_report:
            logger.info(f"[FEATURE_ANALYSIS] Report already exists for experiment {experiment_id}, updating...")
            await self.delete_report(experiment_id)
        
        # 获取实验信息
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.COMPLETED:
            raise ValueError(f"Experiment {experiment_id} is not completed (status: {experiment.status})")
        
        # 获取所有节点
        nodes_result = await self.db.execute(
            select(ExperimentNode)
            .where(ExperimentNode.experiment_id == experiment_id)
            .order_by(ExperimentNode.step)
        )
        all_nodes = list(nodes_result.scalars().all())
        
        # 剔除 buggy nodes
        good_nodes = [n for n in all_nodes if not n.is_buggy and n.metric_value is not None]
        logger.info(f"[FEATURE_ANALYSIS] Total nodes: {len(all_nodes)}, Good nodes: {len(good_nodes)}")
        
        if not good_nodes:
            logger.warning(f"[FEATURE_ANALYSIS] No good nodes found for experiment {experiment_id}")
            return await self.create_report(
                experiment_id=experiment_id,
                error_message="No valid (non-buggy) nodes found for analysis"
            )
        
        # 确定 best_node
        if best_node_id:
            best_node = next((n for n in good_nodes if n.id == best_node_id), None)
        else:
            # 根据 journal_data 中的 lower_is_better 选择最佳节点
            lower_is_better = False
            if experiment.journal_data and isinstance(experiment.journal_data, dict):
                lower_is_better = experiment.journal_data.get('lower_is_better', False)
            
            if lower_is_better:
                best_node = min(good_nodes, key=lambda n: n.metric_value)
            else:
                best_node = max(good_nodes, key=lambda n: n.metric_value)
        
        if not best_node:
            return await self.create_report(
                experiment_id=experiment_id,
                error_message="Could not determine best node for analysis"
            )
        
        logger.info(f"[FEATURE_ANALYSIS] Best node: {best_node.id}, metric: {best_node.metric_value}")
        
        # 加载训练数据
        data_dir = Path(experiment.data_dir)
        train_data = None
        train_file_name = "data.csv"
        
        # 尝试查找训练数据文件
        for file_pattern in ['train.csv', 'data.csv', '*.csv']:
            files = list(data_dir.glob(file_pattern))
            if files:
                train_file = files[0]
                train_file_name = train_file.name
                try:
                    train_data = pd.read_csv(train_file)
                    logger.info(f"[FEATURE_ANALYSIS] Loaded training data from {train_file}: {len(train_data)} rows")
                    break
                except Exception as e:
                    logger.warning(f"[FEATURE_ANALYSIS] Failed to load {train_file}: {e}")
        
        # 初始化分析结果
        analysis_result = AnalysisReport(
            title=f"特征分析报告 - {experiment.name}"
        )
        error_messages = []
        
        # 分析配置
        analysis_config = {
            'label_column': label_column,
            'score_column': score_column,
            'dataset_column': dataset_column,
            'date_column': date_column,
            'data_file': train_file_name,
            'total_nodes': len(all_nodes),
            'good_nodes': len(good_nodes),
            'buggy_nodes': len(all_nodes) - len(good_nodes),
            'best_node_metric': best_node.metric_value
        }
        
        # 1. 建模前数据统计
        if train_data is not None:
            try:
                logger.info("[FEATURE_ANALYSIS] Running DataProfiler...")
                profiler = DataProfiler(
                    label_column=label_column,
                    dataset_column=dataset_column if dataset_column in train_data.columns else None,
                    date_column=date_column if date_column in train_data.columns else None
                )
                data_profile = profiler.profile(train_data, train_file_name)
                analysis_result.data_profile = data_profile
                logger.info(f"[FEATURE_ANALYSIS] DataProfiler completed: {data_profile.sample_count} samples, {data_profile.feature_count} features")
            except Exception as e:
                logger.error(f"[FEATURE_ANALYSIS] DataProfiler failed: {e}")
                error_messages.append(f"DataProfiler: {str(e)}")
        
        # 2. 特征重要性分析 (IV)
        if train_data is not None and label_column in train_data.columns:
            try:
                logger.info("[FEATURE_ANALYSIS] Running FeatureImportance (IV)...")
                fi = FeatureImportance(label_column=label_column)
                # 获取数值特征列
                numeric_cols = train_data.select_dtypes(include=[np.number]).columns.tolist()
                feature_cols = [c for c in numeric_cols if c not in [label_column, dataset_column, date_column, score_column]]
                
                if feature_cols:
                    importance_report = fi.analyze(train_data, feature_columns=feature_cols)
                    analysis_result.feature_importance = importance_report
                    logger.info(f"[FEATURE_ANALYSIS] FeatureImportance completed: {len(importance_report.iv_results)} features analyzed")
            except Exception as e:
                logger.error(f"[FEATURE_ANALYSIS] FeatureImportance failed: {e}")
                error_messages.append(f"FeatureImportance: {str(e)}")
        
        # 3. 特征稳定性分析 (PSI) - 需要时间维度
        if train_data is not None and date_column and date_column in train_data.columns:
            try:
                logger.info("[FEATURE_ANALYSIS] Running FeatureStability (PSI)...")
                fs = FeatureStability(date_column=date_column)
                numeric_cols = train_data.select_dtypes(include=[np.number]).columns.tolist()
                feature_cols = [c for c in numeric_cols if c not in [label_column, dataset_column, date_column, score_column]]
                
                if feature_cols and train_data[date_column].nunique() > 1:
                    stability_report = fs.analyze_feature_stability(train_data, feature_columns=feature_cols)
                    analysis_result.feature_stability = stability_report
                    logger.info(f"[FEATURE_ANALYSIS] FeatureStability completed: {len(stability_report.feature_timelines)} features analyzed")
            except Exception as e:
                logger.error(f"[FEATURE_ANALYSIS] FeatureStability failed: {e}")
                error_messages.append(f"FeatureStability: {str(e)}")
        
        # 4. 模型分析 - 需要分数数据
        # 注意：由于我们没有实际的预测分数，这部分可能需要从 best_node 的执行结果中提取
        # 或者在未来扩展时，运行 best_node 的代码获取预测结果
        
        # 5. 汇总节点性能统计
        node_stats = self._compute_node_statistics(good_nodes)
        analysis_config['node_statistics'] = node_stats
        
        # 生成 Markdown 报告
        try:
            full_report_md = analysis_result.to_markdown()
            
            # 添加节点统计信息到报告
            full_report_md += "\n\n## 节点性能统计\n\n"
            full_report_md += f"- **总节点数**: {len(all_nodes)}\n"
            full_report_md += f"- **有效节点数**: {len(good_nodes)}\n"
            full_report_md += f"- **Buggy 节点数**: {len(all_nodes) - len(good_nodes)}\n"
            full_report_md += f"- **最佳指标值**: {best_node.metric_value}\n\n"
            
            if node_stats:
                full_report_md += "### 有效节点指标分布\n\n"
                full_report_md += f"- **均值**: {node_stats.get('mean', 'N/A'):.4f}\n"
                full_report_md += f"- **标准差**: {node_stats.get('std', 'N/A'):.4f}\n"
                full_report_md += f"- **最小值**: {node_stats.get('min', 'N/A'):.4f}\n"
                full_report_md += f"- **最大值**: {node_stats.get('max', 'N/A'):.4f}\n"
                full_report_md += f"- **中位数**: {node_stats.get('median', 'N/A'):.4f}\n"
            
        except Exception as e:
            logger.error(f"[FEATURE_ANALYSIS] Failed to generate Markdown report: {e}")
            full_report_md = f"# 特征分析报告\n\n报告生成失败: {str(e)}"
            error_messages.append(f"Report generation: {str(e)}")
        
        # 创建报告记录
        report = await self.create_report(
            experiment_id=experiment_id,
            best_node_id=best_node.id,
            data_profile=analysis_result.data_profile.to_dict() if analysis_result.data_profile else None,
            feature_importance=analysis_result.feature_importance.to_dict() if analysis_result.feature_importance else None,
            feature_stability=analysis_result.feature_stability.to_dict() if analysis_result.feature_stability else None,
            model_stability=analysis_result.model_stability.to_dict() if analysis_result.model_stability else None,
            model_evaluation=analysis_result.model_evaluation.to_dict() if analysis_result.model_evaluation else None,
            feature_statistics=[s.to_dict() for s in analysis_result.feature_statistics] if analysis_result.feature_statistics else None,
            full_report_md=full_report_md,
            analysis_config=analysis_config,
            error_message="; ".join(error_messages) if error_messages else None
        )
        
        logger.info(f"[FEATURE_ANALYSIS] Analysis report created: {report.id}")
        return report
    
    def _compute_node_statistics(self, good_nodes: List[ExperimentNode]) -> Dict[str, Any]:
        """计算有效节点的性能统计"""
        if not good_nodes:
            return {}
        
        metrics = [n.metric_value for n in good_nodes if n.metric_value is not None]
        
        if not metrics:
            return {}
        
        return {
            'count': len(metrics),
            'mean': float(np.mean(metrics)),
            'std': float(np.std(metrics)),
            'min': float(np.min(metrics)),
            'max': float(np.max(metrics)),
            'median': float(np.median(metrics))
        }
