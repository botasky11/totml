"""
ModelStability - 模型稳定性分析

功能：
- 计算模型分数的 PSI
- 分析模型分数分布的时间变化
- 生成模型稳定性报告
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class ScoreDistribution:
    """分数分布"""
    period: str
    bins: List[Dict[str, Any]] = field(default_factory=list)
    mean_score: float = 0.0
    std_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0
    median_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'period': self.period,
            'bins': self.bins,
            'mean_score': round(self.mean_score, 4),
            'std_score': round(self.std_score, 4),
            'min_score': round(self.min_score, 4),
            'max_score': round(self.max_score, 4),
            'median_score': round(self.median_score, 4)
        }


@dataclass
class ModelStabilityResult:
    """模型稳定性分析结果"""
    score_column: str
    base_period: str
    psi_timeline: List[Dict[str, Any]] = field(default_factory=list)
    score_distributions: List[ScoreDistribution] = field(default_factory=list)
    overall_psi: float = 0.0
    is_stable: bool = True
    
    @property
    def stability_level(self) -> str:
        """稳定性评级"""
        if self.overall_psi < 0.1:
            return "稳定"
        elif self.overall_psi < 0.25:
            return "轻微变化"
        else:
            return "显著变化"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'score_column': self.score_column,
            'base_period': self.base_period,
            'psi_timeline': self.psi_timeline,
            'score_distributions': [d.to_dict() for d in self.score_distributions],
            'overall_psi': round(self.overall_psi, 6),
            'is_stable': self.is_stable,
            'stability_level': self.stability_level
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "## 模型稳定性分析",
            "",
            f"**分数列**: {self.score_column}",
            f"**基准期**: {self.base_period}",
            f"**整体 PSI**: {self.overall_psi:.6f}",
            f"**稳定性**: {self.stability_level}",
            ""
        ]
        
        # PSI 时间线
        if self.psi_timeline:
            lines.extend([
                "### 模型分数 PSI 变化",
                "",
                "| 时期 | PSI | 状态 |",
                "|------|-----|------|"
            ])
            for item in self.psi_timeline:
                status = "✅" if item['psi'] < 0.25 else "⚠️"
                lines.append(
                    f"| {item['period']} | {item['psi']:.6f} | {status} |"
                )
            lines.append("")
        
        # 分数分布变化
        if self.score_distributions:
            lines.extend([
                "### 模型分数分布变化",
                "",
                "| 时期 | 均值 | 标准差 | 最小值 | 中位数 | 最大值 |",
                "|------|------|--------|--------|--------|--------|"
            ])
            for dist in self.score_distributions:
                lines.append(
                    f"| {dist.period} | {dist.mean_score:.4f} | {dist.std_score:.4f} | "
                    f"{dist.min_score:.4f} | {dist.median_score:.4f} | {dist.max_score:.4f} |"
                )
            lines.append("")
        
        return "\n".join(lines)


class ModelStability:
    """模型稳定性分析器"""
    
    def __init__(
        self,
        n_bins: int = 10,
        score_column: str = 'score',
        period_column: str = 'dt'
    ):
        """
        初始化模型稳定性分析器
        
        Args:
            n_bins: PSI 分箱数量
            score_column: 分数列名
            period_column: 时间周期列名
        """
        self.n_bins = n_bins
        self.score_column = score_column
        self.period_column = period_column
    
    def analyze(
        self,
        data: pd.DataFrame,
        base_period: Optional[str] = None,
        score_column: Optional[str] = None,
        period_column: Optional[str] = None
    ) -> ModelStabilityResult:
        """
        分析模型稳定性
        
        Args:
            data: 包含分数和时间的数据
            base_period: 基准期
            score_column: 分数列名（覆盖初始化设置）
            period_column: 时间列名（覆盖初始化设置）
            
        Returns:
            模型稳定性分析结果
        """
        score_col = score_column or self.score_column
        period_col = period_column or self.period_column
        
        if score_col not in data.columns:
            raise ValueError(f"Score column '{score_col}' not found")
        
        if period_col not in data.columns:
            raise ValueError(f"Period column '{period_col}' not found")
        
        # 获取所有时期
        all_periods = sorted(data[period_col].unique())
        
        if len(all_periods) < 1:
            return ModelStabilityResult(
                score_column=score_col,
                base_period="N/A"
            )
        
        # 确定基准期
        if base_period is None:
            base_period = str(all_periods[-1])  # 默认使用最新一期
        
        base_data = data[data[period_col].astype(str) == str(base_period)]
        
        # 计算分数分布
        score_distributions = []
        psi_timeline = []
        
        # 使用基准期数据创建分箱
        base_scores = base_data[score_col].dropna()
        try:
            _, bin_edges = pd.qcut(base_scores, q=self.n_bins, retbins=True, duplicates='drop')
        except ValueError:
            _, bin_edges = pd.cut(base_scores, bins=self.n_bins, retbins=True, duplicates='drop')
        
        bin_edges[0] = float('-inf')
        bin_edges[-1] = float('inf')
        
        for period in all_periods:
            period_data = data[data[period_col].astype(str) == str(period)]
            scores = period_data[score_col].dropna()
            
            if len(scores) == 0:
                continue
            
            # 计算分布统计
            dist = ScoreDistribution(
                period=str(period),
                mean_score=float(scores.mean()),
                std_score=float(scores.std()),
                min_score=float(scores.min()),
                max_score=float(scores.max()),
                median_score=float(scores.median())
            )
            
            # 计算各分箱占比
            score_cuts = pd.cut(scores, bins=bin_edges)
            bin_counts = score_cuts.value_counts(normalize=True).sort_index()
            
            bins = []
            for bin_label, pct in bin_counts.items():
                bins.append({
                    'bin': str(bin_label),
                    'pct': round(float(pct), 4)
                })
            dist.bins = bins
            
            score_distributions.append(dist)
            
            # 计算 PSI
            if str(period) != str(base_period):
                psi = self._calculate_psi(base_scores, scores, bin_edges)
                psi_timeline.append({
                    'period': str(period),
                    'psi': psi,
                    'stable': psi < 0.25
                })
        
        # 计算整体 PSI（最后一期与基准期的 PSI）
        overall_psi = 0.0
        if psi_timeline:
            overall_psi = max(item['psi'] for item in psi_timeline)
        
        return ModelStabilityResult(
            score_column=score_col,
            base_period=str(base_period),
            psi_timeline=psi_timeline,
            score_distributions=score_distributions,
            overall_psi=overall_psi,
            is_stable=overall_psi < 0.25
        )
    
    def _calculate_psi(
        self,
        base_scores: pd.Series,
        compare_scores: pd.Series,
        bin_edges: np.ndarray
    ) -> float:
        """计算 PSI"""
        base_cuts = pd.cut(base_scores, bins=bin_edges)
        compare_cuts = pd.cut(compare_scores, bins=bin_edges)
        
        base_pcts = base_cuts.value_counts(normalize=True)
        compare_pcts = compare_cuts.value_counts(normalize=True)
        
        # 对齐索引
        all_bins = base_pcts.index.union(compare_pcts.index)
        base_pcts = base_pcts.reindex(all_bins, fill_value=0.0001).clip(lower=0.0001)
        compare_pcts = compare_pcts.reindex(all_bins, fill_value=0.0001).clip(lower=0.0001)
        
        # 计算 PSI
        psi = ((compare_pcts - base_pcts) * np.log(compare_pcts / base_pcts)).sum()
        return float(psi)
    
    def calculate_score_distribution_by_bins(
        self,
        data: pd.DataFrame,
        score_column: Optional[str] = None,
        n_bins: int = 10,
        custom_bins: Optional[List[float]] = None
    ) -> pd.DataFrame:
        """
        计算分数的分箱分布
        
        Args:
            data: 输入数据
            score_column: 分数列名
            n_bins: 分箱数量
            custom_bins: 自定义分箱边界
            
        Returns:
            分箱分布 DataFrame
        """
        score_col = score_column or self.score_column
        scores = data[score_col].dropna()
        
        if custom_bins is not None:
            cuts = pd.cut(scores, bins=custom_bins)
        else:
            cuts = pd.qcut(scores, q=n_bins, duplicates='drop')
        
        result = cuts.value_counts().sort_index()
        result_df = pd.DataFrame({
            'bin': result.index.astype(str),
            'count': result.values,
            'pct': result.values / len(scores)
        })
        
        return result_df


# 便捷函数
def analyze_model_stability(
    data: pd.DataFrame,
    score_column: str = 'score',
    period_column: str = 'dt',
    n_bins: int = 10
) -> ModelStabilityResult:
    """
    便捷函数：分析模型稳定性
    
    Args:
        data: 输入数据
        score_column: 分数列名
        period_column: 时间列名
        n_bins: 分箱数量
        
    Returns:
        模型稳定性分析结果
    """
    analyzer = ModelStability(
        n_bins=n_bins,
        score_column=score_column,
        period_column=period_column
    )
    return analyzer.analyze(data)
