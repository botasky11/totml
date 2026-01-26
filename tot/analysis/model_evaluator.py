"""
ModelEvaluator - 模型性能评估

功能：
- 计算 AUC、KS、Lift 等模型评估指标
- 按数据集分组评估
- 计算分箱性能 (模型分箱表)
- 生成性能评估报告
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict


@dataclass
class DatasetMetrics:
    """数据集评估指标"""
    dataset_name: str           # 数据集名称
    period: str                 # 时间范围
    auc: float                  # AUC
    ks: float                   # KS
    lift: float                 # Lift
    sample_count: int           # 样本数
    positive_count: int         # 正样本数
    negative_count: int         # 负样本数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dataset_name': self.dataset_name,
            'period': self.period,
            'auc': round(self.auc, 4),
            'ks': round(self.ks, 4),
            'lift': round(self.lift, 4),
            'sample_count': self.sample_count,
            'positive_count': self.positive_count,
            'negative_count': self.negative_count,
            'labels': f"{self.sample_count}/{self.positive_count}/{self.negative_count}"
        }


@dataclass
class BinPerformance:
    """单个分箱的性能"""
    bin_label: str
    bin_range: str
    count: int
    positive_count: int
    negative_count: int
    positive_rate: float
    cumulative_positive_rate: float
    cumulative_negative_rate: float
    ks: float
    lift: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'bin_label': self.bin_label,
            'bin_range': self.bin_range,
            'count': self.count,
            'positive_count': self.positive_count,
            'negative_count': self.negative_count,
            'positive_rate': f"{self.positive_rate:.2%}",
            'cumulative_positive_rate': f"{self.cumulative_positive_rate:.2%}",
            'cumulative_negative_rate': f"{self.cumulative_negative_rate:.2%}",
            'ks': round(self.ks, 4),
            'lift': round(self.lift, 4)
        }


@dataclass
class ModelBinningTable:
    """模型分箱表"""
    score_column: str
    n_bins: int
    bins: List[BinPerformance] = field(default_factory=list)
    max_ks: float = 0.0
    max_ks_bin: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'score_column': self.score_column,
            'n_bins': self.n_bins,
            'bins': [b.to_dict() for b in self.bins],
            'max_ks': round(self.max_ks, 4),
            'max_ks_bin': self.max_ks_bin
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        return pd.DataFrame([b.to_dict() for b in self.bins])


@dataclass
class ModelEvaluationReport:
    """模型评估报告"""
    score_column: str
    label_column: str
    dataset_metrics: List[DatasetMetrics] = field(default_factory=list)
    binning_table: Optional[ModelBinningTable] = None
    overall_auc: float = 0.0
    overall_ks: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'score_column': self.score_column,
            'label_column': self.label_column,
            'dataset_metrics': [m.to_dict() for m in self.dataset_metrics],
            'binning_table': self.binning_table.to_dict() if self.binning_table else None,
            'overall_auc': round(self.overall_auc, 4),
            'overall_ks': round(self.overall_ks, 4)
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "## 模型性能评估",
            "",
            f"**分数列**: {self.score_column}",
            f"**标签列**: {self.label_column}",
            f"**整体 AUC**: {self.overall_auc:.4f}",
            f"**整体 KS**: {self.overall_ks:.4f}",
            ""
        ]
        
        # 数据集指标
        if self.dataset_metrics:
            lines.extend([
                "### 分数据集性能指标",
                "",
                "| 数据集 | 时间范围 | AUC | KS | Lift | 样本数 | 正/负样本 |",
                "|--------|----------|-----|----|----|--------|-----------|"
            ])
            for m in self.dataset_metrics:
                lines.append(
                    f"| {m.dataset_name} | {m.period} | {m.auc:.4f} | {m.ks:.4f} | "
                    f"{m.lift:.4f} | {m.sample_count} | {m.positive_count}/{m.negative_count} |"
                )
            lines.append("")
        
        # 分箱表
        if self.binning_table and self.binning_table.bins:
            lines.extend([
                "### 模型分箱性能",
                "",
                f"**最大 KS**: {self.binning_table.max_ks:.4f} (分箱: {self.binning_table.max_ks_bin})",
                "",
                "| 分箱 | 范围 | 样本数 | 正样本数 | 正样本率 | 累计正样本率 | 累计负样本率 | KS | Lift |",
                "|------|------|--------|----------|----------|--------------|--------------|-----|------|"
            ])
            for b in self.binning_table.bins:
                lines.append(
                    f"| {b.bin_label} | {b.bin_range} | {b.count} | {b.positive_count} | "
                    f"{b.positive_rate:.2%} | {b.cumulative_positive_rate:.2%} | "
                    f"{b.cumulative_negative_rate:.2%} | {b.ks:.4f} | {b.lift:.4f} |"
                )
            lines.append("")
        
        return "\n".join(lines)


class ModelEvaluator:
    """模型性能评估器"""
    
    def __init__(
        self,
        score_column: str = 'score',
        label_column: str = 'default_flag',
        dataset_column: Optional[str] = 'dataset',
        date_column: Optional[str] = 'dt',
        n_bins: int = 10,
        positive_label: int = 1
    ):
        """
        初始化模型评估器
        
        Args:
            score_column: 分数列名
            label_column: 标签列名
            dataset_column: 数据集划分列名
            date_column: 日期列名
            n_bins: 分箱数量
            positive_label: 正样本标签值
        """
        self.score_column = score_column
        self.label_column = label_column
        self.dataset_column = dataset_column
        self.date_column = date_column
        self.n_bins = n_bins
        self.positive_label = positive_label
    
    def calculate_auc(
        self,
        scores: np.ndarray,
        labels: np.ndarray
    ) -> float:
        """
        计算 AUC
        
        使用梯形法则计算 ROC 曲线下面积
        """
        # 按分数排序
        sorted_indices = np.argsort(scores)[::-1]
        sorted_labels = labels[sorted_indices]
        
        # 计算累计正负样本
        n_pos = np.sum(labels == self.positive_label)
        n_neg = len(labels) - n_pos
        
        if n_pos == 0 or n_neg == 0:
            return 0.5
        
        tpr = np.cumsum(sorted_labels == self.positive_label) / n_pos
        fpr = np.cumsum(sorted_labels != self.positive_label) / n_neg
        
        # 添加起点
        tpr = np.concatenate([[0], tpr])
        fpr = np.concatenate([[0], fpr])
        
        # 使用梯形法则计算面积
        auc = np.trapz(tpr, fpr)
        return float(auc)
    
    def calculate_ks(
        self,
        scores: np.ndarray,
        labels: np.ndarray
    ) -> Tuple[float, int]:
        """
        计算 KS 值
        
        Returns:
            (KS值, 最大KS对应的分位数)
        """
        sorted_indices = np.argsort(scores)[::-1]
        sorted_labels = labels[sorted_indices]
        
        n_pos = np.sum(labels == self.positive_label)
        n_neg = len(labels) - n_pos
        
        if n_pos == 0 or n_neg == 0:
            return 0.0, 0
        
        cum_pos = np.cumsum(sorted_labels == self.positive_label) / n_pos
        cum_neg = np.cumsum(sorted_labels != self.positive_label) / n_neg
        
        ks_values = np.abs(cum_pos - cum_neg)
        max_ks_idx = np.argmax(ks_values)
        
        return float(ks_values[max_ks_idx]), int(max_ks_idx)
    
    def calculate_lift(
        self,
        scores: np.ndarray,
        labels: np.ndarray,
        top_pct: float = 0.1
    ) -> float:
        """
        计算 Lift 值
        
        Args:
            scores: 预测分数
            labels: 真实标签
            top_pct: 取前 top_pct 计算 lift
            
        Returns:
            Lift 值
        """
        n = len(scores)
        top_n = max(int(n * top_pct), 1)
        
        sorted_indices = np.argsort(scores)[::-1]
        top_labels = labels[sorted_indices[:top_n]]
        
        overall_positive_rate = np.mean(labels == self.positive_label)
        top_positive_rate = np.mean(top_labels == self.positive_label)
        
        if overall_positive_rate == 0:
            return 0.0
        
        return float(top_positive_rate / overall_positive_rate)
    
    def evaluate_dataset(
        self,
        data: pd.DataFrame,
        dataset_name: str,
        period: str = ""
    ) -> DatasetMetrics:
        """
        评估单个数据集
        """
        scores = data[self.score_column].values
        labels = data[self.label_column].values
        
        auc = self.calculate_auc(scores, labels)
        ks, _ = self.calculate_ks(scores, labels)
        lift = self.calculate_lift(scores, labels)
        
        sample_count = len(data)
        positive_count = int(np.sum(labels == self.positive_label))
        negative_count = sample_count - positive_count
        
        return DatasetMetrics(
            dataset_name=dataset_name,
            period=period,
            auc=auc,
            ks=ks,
            lift=lift,
            sample_count=sample_count,
            positive_count=positive_count,
            negative_count=negative_count
        )
    
    def calculate_binning_table(
        self,
        data: pd.DataFrame,
        n_bins: Optional[int] = None
    ) -> ModelBinningTable:
        """
        计算模型分箱表
        """
        n_bins = n_bins or self.n_bins
        
        scores = data[self.score_column].values
        labels = data[self.label_column].values
        
        # 创建分箱
        try:
            data_copy = data[[self.score_column, self.label_column]].copy()
            data_copy['bin'] = pd.qcut(
                data_copy[self.score_column],
                q=n_bins,
                duplicates='drop',
                labels=False
            )
        except ValueError:
            data_copy = data[[self.score_column, self.label_column]].copy()
            data_copy['bin'] = pd.cut(
                data_copy[self.score_column],
                bins=n_bins,
                labels=False,
                duplicates='drop'
            )
        
        # 计算各分箱统计
        total_positive = (labels == self.positive_label).sum()
        total_negative = len(labels) - total_positive
        overall_positive_rate = total_positive / len(labels) if len(labels) > 0 else 0
        
        bins_list = []
        cum_positive = 0
        cum_negative = 0
        max_ks = 0.0
        max_ks_bin = ""
        
        for bin_idx in sorted(data_copy['bin'].dropna().unique()):
            bin_data = data_copy[data_copy['bin'] == bin_idx]
            
            count = len(bin_data)
            positive_count = (bin_data[self.label_column] == self.positive_label).sum()
            negative_count = count - positive_count
            positive_rate = positive_count / count if count > 0 else 0
            
            cum_positive += positive_count
            cum_negative += negative_count
            
            cum_positive_rate = cum_positive / total_positive if total_positive > 0 else 0
            cum_negative_rate = cum_negative / total_negative if total_negative > 0 else 0
            
            ks = abs(cum_positive_rate - cum_negative_rate)
            lift = positive_rate / overall_positive_rate if overall_positive_rate > 0 else 0
            
            # 计算分箱范围
            bin_min = bin_data[self.score_column].min()
            bin_max = bin_data[self.score_column].max()
            bin_range = f"[{bin_min:.4f}, {bin_max:.4f}]"
            
            bin_label = f"Bin {int(bin_idx) + 1}"
            
            if ks > max_ks:
                max_ks = ks
                max_ks_bin = bin_label
            
            bins_list.append(BinPerformance(
                bin_label=bin_label,
                bin_range=bin_range,
                count=int(count),
                positive_count=int(positive_count),
                negative_count=int(negative_count),
                positive_rate=positive_rate,
                cumulative_positive_rate=cum_positive_rate,
                cumulative_negative_rate=cum_negative_rate,
                ks=ks,
                lift=lift
            ))
        
        return ModelBinningTable(
            score_column=self.score_column,
            n_bins=n_bins,
            bins=bins_list,
            max_ks=max_ks,
            max_ks_bin=max_ks_bin
        )
    
    def evaluate(
        self,
        data: pd.DataFrame,
        include_binning: bool = True
    ) -> ModelEvaluationReport:
        """
        执行完整的模型评估
        
        Args:
            data: 输入数据
            include_binning: 是否包含分箱表
            
        Returns:
            模型评估报告
        """
        report = ModelEvaluationReport(
            score_column=self.score_column,
            label_column=self.label_column
        )
        
        # 按数据集分组评估
        if self.dataset_column and self.dataset_column in data.columns:
            order = ['train', 'valid', 'test', 'oot']
            groups = list(data.groupby(self.dataset_column))
            groups.sort(
                key=lambda x: order.index(x[0]) if x[0] in order else len(order)
            )
            
            for name, group_data in groups:
                # 获取时间范围
                if self.date_column and self.date_column in data.columns:
                    dt_min = group_data[self.date_column].min()
                    dt_max = group_data[self.date_column].max()
                    period = f"{dt_min}-{dt_max}"
                else:
                    period = ""
                
                metrics = self.evaluate_dataset(group_data, str(name), period)
                report.dataset_metrics.append(metrics)
        
        # 整体评估
        scores = data[self.score_column].values
        labels = data[self.label_column].values
        
        report.overall_auc = self.calculate_auc(scores, labels)
        report.overall_ks, _ = self.calculate_ks(scores, labels)
        
        # 分箱表
        if include_binning:
            report.binning_table = self.calculate_binning_table(data)
        
        return report


# 便捷函数
def evaluate_model(
    data: pd.DataFrame,
    score_column: str = 'score',
    label_column: str = 'default_flag',
    dataset_column: Optional[str] = 'dataset',
    n_bins: int = 10
) -> ModelEvaluationReport:
    """
    便捷函数：评估模型性能
    
    Args:
        data: 输入数据
        score_column: 分数列名
        label_column: 标签列名
        dataset_column: 数据集列名
        n_bins: 分箱数量
        
    Returns:
        模型评估报告
    """
    evaluator = ModelEvaluator(
        score_column=score_column,
        label_column=label_column,
        dataset_column=dataset_column,
        n_bins=n_bins
    )
    return evaluator.evaluate(data)
