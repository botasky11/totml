"""
特征分析模块 - 参考蚂蚁数科风控智能体 AgentAR 实现

该模块提供：
1. 建模前样本数据统计功能 (DataProfiler)
2. 建模后评估分析报告 (FeatureAnalyzer)
   - 特征重要性分析 (IV)
   - 特征稳定性分析 (PSI)
   - 模型稳定性分析
   - 模型性能评估 (AUC/KS/Lift)
   - 综合报告生成
"""

from .data_profiler import DataProfiler
from .feature_importance import FeatureImportance
from .feature_stability import FeatureStability
from .model_stability import ModelStability
from .model_evaluator import ModelEvaluator
from .report_generator import ReportGenerator

__all__ = [
    'DataProfiler',
    'FeatureImportance', 
    'FeatureStability',
    'ModelStability',
    'ModelEvaluator',
    'ReportGenerator',
]
