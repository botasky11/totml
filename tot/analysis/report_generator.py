"""
ReportGenerator - 综合报告生成

功能：
- 整合所有分析结果
- 生成 Markdown 格式的完整报告
- 支持 HTML 报告输出
- 支持 JSON 数据导出
"""

import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

from .data_profiler import DataProfileResult, DataProfiler
from .feature_importance import FeatureImportanceReport, FeatureImportance
from .feature_stability import FeatureStabilityReport, FeatureStability
from .model_stability import ModelStabilityResult, ModelStability
from .model_evaluator import ModelEvaluationReport, ModelEvaluator


@dataclass
class FeatureStatistics:
    """特征统计信息"""
    feature: str
    missing_rate: float
    mode_rate: float
    mean: Optional[float] = None
    median: Optional[float] = None
    ks: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'col': self.feature,
            'missing_rate': f"{self.missing_rate:.4f}",
            'mode_rate': f"{self.mode_rate:.4f}",
            'mean': round(self.mean, 4) if self.mean is not None else None,
            'median': round(self.median, 4) if self.median is not None else None,
            'ks': round(self.ks, 4) if self.ks is not None else None
        }


@dataclass
class ModelParameters:
    """模型参数"""
    model_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_type': self.model_type,
            'parameters': self.parameters
        }


@dataclass
class AnalysisReport:
    """综合分析报告"""
    title: str = "特征分析报告"
    generated_at: str = ""
    
    # 各部分分析结果
    data_profile: Optional[DataProfileResult] = None
    feature_importance: Optional[FeatureImportanceReport] = None
    feature_stability: Optional[FeatureStabilityReport] = None
    model_stability: Optional[ModelStabilityResult] = None
    model_evaluation: Optional[ModelEvaluationReport] = None
    feature_statistics: List[FeatureStatistics] = field(default_factory=list)
    model_parameters: Optional[ModelParameters] = None
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'title': self.title,
            'generated_at': self.generated_at,
        }
        
        if self.data_profile:
            result['data_profile'] = self.data_profile.to_dict()
        if self.feature_importance:
            result['feature_importance'] = self.feature_importance.to_dict()
        if self.feature_stability:
            result['feature_stability'] = self.feature_stability.to_dict()
        if self.model_stability:
            result['model_stability'] = self.model_stability.to_dict()
        if self.model_evaluation:
            result['model_evaluation'] = self.model_evaluation.to_dict()
        if self.feature_statistics:
            result['feature_statistics'] = [s.to_dict() for s in self.feature_statistics]
        if self.model_parameters:
            result['model_parameters'] = self.model_parameters.to_dict()
        
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            f"# {self.title}",
            "",
            f"**生成时间**: {self.generated_at}",
            "",
            "---",
            ""
        ]
        
        # 目录
        lines.extend([
            "## 目录",
            "",
            "1. [样本数据统计](#样本数据统计)",
            "2. [特征重要性分析](#特征重要性分析)",
            "3. [特征稳定性分析](#特征稳定性分析psi)",
            "4. [模型稳定性分析](#模型稳定性分析)",
            "5. [模型性能评估](#模型性能评估)",
            "6. [特征统计指标](#特征统计指标)",
            "7. [模型参数](#模型参数)",
            "",
            "---",
            ""
        ])
        
        # 1. 样本数据统计
        if self.data_profile:
            lines.append(self.data_profile.to_markdown())
            lines.append("")
        
        # 2. 特征重要性分析
        if self.feature_importance:
            lines.append(self.feature_importance.to_markdown())
            lines.append("")
        
        # 3. 特征稳定性分析
        if self.feature_stability:
            lines.append(self.feature_stability.to_markdown())
            lines.append("")
        
        # 4. 模型稳定性分析
        if self.model_stability:
            lines.append(self.model_stability.to_markdown())
            lines.append("")
        
        # 5. 模型性能评估
        if self.model_evaluation:
            lines.append(self.model_evaluation.to_markdown())
            lines.append("")
        
        # 6. 特征统计指标
        if self.feature_statistics:
            lines.extend([
                "## 特征统计指标",
                "",
                "| 特征名 | 缺失率 | 众数率 | 均值 | 中位数 | KS |",
                "|--------|--------|--------|------|--------|-----|"
            ])
            for stat in self.feature_statistics[:20]:  # 只显示前20个
                mean_str = f"{stat.mean:.4f}" if stat.mean is not None else "-"
                median_str = f"{stat.median:.4f}" if stat.median is not None else "-"
                ks_str = f"{stat.ks:.4f}" if stat.ks is not None else "-"
                lines.append(
                    f"| {stat.feature} | {stat.missing_rate:.4f} | "
                    f"{stat.mode_rate:.4f} | {mean_str} | {median_str} | {ks_str} |"
                )
            lines.extend(["", ""])
        
        # 7. 模型参数
        if self.model_parameters:
            lines.extend([
                "## 模型参数",
                "",
                f"**模型类型**: {self.model_parameters.model_type}",
                "",
                "### 参数配置",
                "",
                "```json",
                json.dumps(self.model_parameters.parameters, indent=2, ensure_ascii=False),
                "```",
                ""
            ])
        
        return "\n".join(lines)
    
    def save_markdown(self, file_path: str) -> str:
        """保存 Markdown 报告到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.to_markdown()
        path.write_text(content, encoding='utf-8')
        
        return str(path.absolute())
    
    def save_json(self, file_path: str) -> str:
        """保存 JSON 数据到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.to_json()
        path.write_text(content, encoding='utf-8')
        
        return str(path.absolute())


class ReportGenerator:
    """综合报告生成器"""
    
    def __init__(
        self,
        label_column: str = 'default_flag',
        score_column: str = 'score',
        dataset_column: Optional[str] = 'dataset',
        date_column: Optional[str] = 'dt',
        n_bins: int = 10
    ):
        """
        初始化报告生成器
        
        Args:
            label_column: 标签列名
            score_column: 分数列名
            dataset_column: 数据集划分列名
            date_column: 日期列名
            n_bins: 分箱数量
        """
        self.label_column = label_column
        self.score_column = score_column
        self.dataset_column = dataset_column
        self.date_column = date_column
        self.n_bins = n_bins
        
        # 初始化各分析器
        self.data_profiler = DataProfiler(
            label_column=label_column,
            dataset_column=dataset_column,
            date_column=date_column
        )
        self.feature_importance = FeatureImportance(
            label_column=label_column,
            n_bins=n_bins
        )
        self.feature_stability = FeatureStability(
            n_bins=n_bins,
            date_column=date_column
        )
        self.model_stability = ModelStability(
            n_bins=n_bins,
            score_column=score_column,
            period_column=date_column
        )
        self.model_evaluator = ModelEvaluator(
            score_column=score_column,
            label_column=label_column,
            dataset_column=dataset_column,
            date_column=date_column,
            n_bins=n_bins
        )
    
    def generate_pre_modeling_report(
        self,
        data: pd.DataFrame,
        file_name: str = "train.csv",
        title: str = "建模前样本数据统计报告"
    ) -> AnalysisReport:
        """
        生成建模前的数据统计报告
        
        Args:
            data: 输入数据
            file_name: 数据文件名
            title: 报告标题
            
        Returns:
            分析报告
        """
        report = AnalysisReport(title=title)
        
        # 数据概况
        report.data_profile = self.data_profiler.profile(data, file_name)
        
        # 特征统计
        feature_stats = self._compute_feature_statistics(data)
        report.feature_statistics = feature_stats
        
        return report
    
    def generate_post_modeling_report(
        self,
        data: pd.DataFrame,
        model: Any = None,
        model_type: str = "Unknown",
        model_params: Optional[Dict[str, Any]] = None,
        title: str = "建模后评估分析报告"
    ) -> AnalysisReport:
        """
        生成建模后的评估分析报告
        
        Args:
            data: 包含分数和标签的数据
            model: 训练好的模型
            model_type: 模型类型
            model_params: 模型参数
            title: 报告标题
            
        Returns:
            分析报告
        """
        report = AnalysisReport(title=title)
        
        # 获取特征列
        exclude_cols = {
            self.label_column,
            self.score_column,
            self.dataset_column,
            self.date_column
        }
        feature_columns = [
            c for c in data.select_dtypes(include=[np.number]).columns
            if c not in exclude_cols
        ]
        
        # 1. 特征重要性分析
        try:
            importance_report = self.feature_importance.analyze(
                data,
                model=model,
                feature_columns=feature_columns
            )
            report.feature_importance = importance_report
        except Exception as e:
            print(f"Warning: Failed to calculate feature importance: {e}")
        
        # 2. 特征稳定性分析（如果有时间维度）
        if self.date_column and self.date_column in data.columns:
            try:
                stability_report = self.feature_stability.analyze_feature_stability(
                    data,
                    feature_columns=feature_columns
                )
                report.feature_stability = stability_report
            except Exception as e:
                print(f"Warning: Failed to analyze feature stability: {e}")
        
        # 3. 模型稳定性分析
        if self.score_column in data.columns and self.date_column in data.columns:
            try:
                model_stability_result = self.model_stability.analyze(data)
                report.model_stability = model_stability_result
            except Exception as e:
                print(f"Warning: Failed to analyze model stability: {e}")
        
        # 4. 模型性能评估
        if self.score_column in data.columns:
            try:
                evaluation_report = self.model_evaluator.evaluate(data)
                report.model_evaluation = evaluation_report
            except Exception as e:
                print(f"Warning: Failed to evaluate model: {e}")
        
        # 5. 特征统计
        feature_stats = self._compute_feature_statistics(data, feature_columns)
        report.feature_statistics = feature_stats
        
        # 6. 模型参数
        if model_params or model_type != "Unknown":
            report.model_parameters = ModelParameters(
                model_type=model_type,
                parameters=model_params or {}
            )
        
        return report
    
    def generate_full_report(
        self,
        train_data: pd.DataFrame,
        scored_data: Optional[pd.DataFrame] = None,
        model: Any = None,
        model_type: str = "Unknown",
        model_params: Optional[Dict[str, Any]] = None,
        file_name: str = "train.csv",
        title: str = "风控特征分析报告"
    ) -> AnalysisReport:
        """
        生成完整的分析报告（建模前 + 建模后）
        
        Args:
            train_data: 训练数据
            scored_data: 带分数的数据（用于评估）
            model: 训练好的模型
            model_type: 模型类型
            model_params: 模型参数
            file_name: 数据文件名
            title: 报告标题
            
        Returns:
            完整分析报告
        """
        report = AnalysisReport(title=title)
        
        # 建模前：数据概况
        report.data_profile = self.data_profiler.profile(train_data, file_name)
        
        # 使用带分数的数据进行后续分析
        eval_data = scored_data if scored_data is not None else train_data
        
        # 获取特征列
        exclude_cols = {
            self.label_column,
            self.score_column,
            self.dataset_column,
            self.date_column
        }
        feature_columns = [
            c for c in eval_data.select_dtypes(include=[np.number]).columns
            if c not in exclude_cols
        ]
        
        # 特征重要性
        try:
            importance_report = self.feature_importance.analyze(
                train_data,
                model=model,
                feature_columns=feature_columns
            )
            report.feature_importance = importance_report
        except Exception as e:
            print(f"Warning: Failed to calculate feature importance: {e}")
        
        # 特征稳定性
        if self.date_column and self.date_column in eval_data.columns:
            try:
                stability_report = self.feature_stability.analyze_feature_stability(
                    eval_data,
                    feature_columns=feature_columns
                )
                report.feature_stability = stability_report
            except Exception as e:
                print(f"Warning: Failed to analyze feature stability: {e}")
        
        # 模型稳定性
        if scored_data is not None and self.score_column in scored_data.columns:
            try:
                model_stability_result = self.model_stability.analyze(scored_data)
                report.model_stability = model_stability_result
            except Exception as e:
                print(f"Warning: Failed to analyze model stability: {e}")
        
        # 模型评估
        if scored_data is not None and self.score_column in scored_data.columns:
            try:
                evaluation_report = self.model_evaluator.evaluate(scored_data)
                report.model_evaluation = evaluation_report
            except Exception as e:
                print(f"Warning: Failed to evaluate model: {e}")
        
        # 特征统计
        feature_stats = self._compute_feature_statistics(train_data, feature_columns)
        report.feature_statistics = feature_stats
        
        # 模型参数
        if model_params or model_type != "Unknown":
            report.model_parameters = ModelParameters(
                model_type=model_type,
                parameters=model_params or {}
            )
        
        return report
    
    def _compute_feature_statistics(
        self,
        data: pd.DataFrame,
        feature_columns: Optional[List[str]] = None
    ) -> List[FeatureStatistics]:
        """计算特征统计指标"""
        if feature_columns is None:
            exclude_cols = {
                self.label_column,
                self.score_column,
                self.dataset_column,
                self.date_column
            }
            feature_columns = [
                c for c in data.columns
                if c not in exclude_cols
            ]
        
        stats = []
        for col in feature_columns[:50]:  # 限制数量
            try:
                col_data = data[col]
                
                # 缺失率
                missing_rate = col_data.isna().mean()
                
                # 众数率
                mode_value = col_data.mode()
                if len(mode_value) > 0:
                    mode_rate = (col_data == mode_value.iloc[0]).mean()
                else:
                    mode_rate = 0.0
                
                # 数值统计
                mean_val = None
                median_val = None
                if pd.api.types.is_numeric_dtype(col_data):
                    mean_val = col_data.mean()
                    median_val = col_data.median()
                
                stats.append(FeatureStatistics(
                    feature=col,
                    missing_rate=missing_rate,
                    mode_rate=mode_rate,
                    mean=mean_val,
                    median=median_val
                ))
            except Exception as e:
                continue
        
        return stats


# 便捷函数
def generate_analysis_report(
    data: pd.DataFrame,
    model: Any = None,
    label_column: str = 'default_flag',
    score_column: str = 'score',
    dataset_column: Optional[str] = 'dataset',
    date_column: Optional[str] = 'dt',
    title: str = "特征分析报告"
) -> AnalysisReport:
    """
    便捷函数：生成特征分析报告
    
    Args:
        data: 输入数据
        model: 可选的训练模型
        label_column: 标签列名
        score_column: 分数列名
        dataset_column: 数据集列名
        date_column: 日期列名
        title: 报告标题
        
    Returns:
        分析报告
    """
    generator = ReportGenerator(
        label_column=label_column,
        score_column=score_column,
        dataset_column=dataset_column,
        date_column=date_column
    )
    
    # 判断是建模前还是建模后
    if score_column in data.columns:
        return generator.generate_post_modeling_report(
            data,
            model=model,
            title=title
        )
    else:
        return generator.generate_pre_modeling_report(
            data,
            title=title
        )
