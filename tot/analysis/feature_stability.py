"""
FeatureStability - 特征稳定性分析 (PSI)

功能：
- 计算特征 PSI (Population Stability Index) 值
- 按时间维度分析特征稳定性
- 支持特征稳定性预警
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import warnings


@dataclass
class PSIResult:
    """单个特征的 PSI 计算结果"""
    feature: str
    psi: float
    base_period: str
    compare_period: str
    bin_details: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def stability_level(self) -> str:
        """稳定性评级"""
        if self.psi < 0.1:
            return "稳定"
        elif self.psi < 0.25:
            return "轻微变化"
        else:
            return "显著变化"
    
    @property
    def stability_color(self) -> str:
        """稳定性颜色标记"""
        if self.psi < 0.1:
            return "green"
        elif self.psi < 0.25:
            return "yellow"
        else:
            return "red"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'feature': self.feature,
            'psi': round(self.psi, 6),
            'base_period': self.base_period,
            'compare_period': self.compare_period,
            'stability_level': self.stability_level,
            'stability_color': self.stability_color,
            'bin_details': self.bin_details
        }


@dataclass
class FeatureStabilityTimeline:
    """特征稳定性时间线"""
    feature: str
    timeline: List[PSIResult] = field(default_factory=list)
    
    @property
    def max_psi(self) -> float:
        """最大 PSI 值"""
        if not self.timeline:
            return 0.0
        return max(r.psi for r in self.timeline)
    
    @property
    def avg_psi(self) -> float:
        """平均 PSI 值"""
        if not self.timeline:
            return 0.0
        return sum(r.psi for r in self.timeline) / len(self.timeline)
    
    @property
    def is_stable(self) -> bool:
        """是否整体稳定"""
        return self.max_psi < 0.25
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'feature': self.feature,
            'max_psi': round(self.max_psi, 6),
            'avg_psi': round(self.avg_psi, 6),
            'is_stable': self.is_stable,
            'timeline': [r.to_dict() for r in self.timeline]
        }


@dataclass
class FeatureStabilityReport:
    """特征稳定性分析报告"""
    base_period: str
    feature_timelines: List[FeatureStabilityTimeline] = field(default_factory=list)
    
    def get_unstable_features(self, threshold: float = 0.25) -> List[str]:
        """获取不稳定的特征列表"""
        return [
            ft.feature for ft in self.feature_timelines 
            if ft.max_psi >= threshold
        ]
    
    def get_feature_psi_summary(self) -> pd.DataFrame:
        """获取特征 PSI 汇总表"""
        data = []
        for ft in self.feature_timelines:
            for psi_result in ft.timeline:
                data.append({
                    'feature': ft.feature,
                    'period': psi_result.compare_period,
                    'psi': psi_result.psi,
                    'stability': psi_result.stability_level
                })
        return pd.DataFrame(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'base_period': self.base_period,
            'feature_timelines': [ft.to_dict() for ft in self.feature_timelines],
            'unstable_features': self.get_unstable_features()
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "## 特征稳定性分析 (PSI)",
            "",
            f"**基准期**: {self.base_period}",
            ""
        ]
        
        # 汇总表
        if self.feature_timelines:
            lines.extend([
                "### 特征 PSI 汇总",
                "",
                "| 特征名 | 最大 PSI | 平均 PSI | 稳定性 |",
                "|--------|----------|----------|--------|"
            ])
            
            # 按最大 PSI 排序
            sorted_timelines = sorted(
                self.feature_timelines,
                key=lambda x: x.max_psi,
                reverse=True
            )
            
            for ft in sorted_timelines[:20]:  # 只显示前 20 个
                stability = "✅ 稳定" if ft.is_stable else "⚠️ 不稳定"
                lines.append(
                    f"| {ft.feature} | {ft.max_psi:.6f} | {ft.avg_psi:.6f} | {stability} |"
                )
            lines.append("")
        
        # 不稳定特征警告
        unstable = self.get_unstable_features()
        if unstable:
            lines.extend([
                "### ⚠️ 不稳定特征警告",
                "",
                f"以下 {len(unstable)} 个特征的 PSI 超过 0.25 阈值：",
                ""
            ])
            for feature in unstable:
                lines.append(f"- {feature}")
            lines.append("")
        
        return "\n".join(lines)


class FeatureStability:
    """特征稳定性分析器"""
    
    def __init__(
        self,
        n_bins: int = 10,
        date_column: str = 'dt',
        date_format: Optional[str] = None
    ):
        """
        初始化特征稳定性分析器
        
        Args:
            n_bins: PSI 分箱数量
            date_column: 日期列名
            date_format: 日期格式（如 '%Y%m%d'）
        """
        self.n_bins = n_bins
        self.date_column = date_column
        self.date_format = date_format
    
    def calculate_psi(
        self,
        base_data: pd.Series,
        compare_data: pd.Series,
        feature_name: str,
        base_period: str = "base",
        compare_period: str = "compare"
    ) -> PSIResult:
        """
        计算两个分布之间的 PSI
        
        Args:
            base_data: 基准期数据
            compare_data: 对比期数据
            feature_name: 特征名称
            base_period: 基准期名称
            compare_period: 对比期名称
            
        Returns:
            PSI 计算结果
        """
        # 移除缺失值
        base_data = base_data.dropna()
        compare_data = compare_data.dropna()
        
        if len(base_data) == 0 or len(compare_data) == 0:
            return PSIResult(
                feature=feature_name,
                psi=0.0,
                base_period=base_period,
                compare_period=compare_period
            )
        
        # 使用基准期数据创建分箱
        try:
            _, bin_edges = pd.qcut(base_data, q=self.n_bins, retbins=True, duplicates='drop')
        except ValueError:
            # 如果无法等频分箱，使用等宽分箱
            _, bin_edges = pd.cut(base_data, bins=self.n_bins, retbins=True, duplicates='drop')
        
        # 确保边界包含所有值
        bin_edges[0] = float('-inf')
        bin_edges[-1] = float('inf')
        
        # 计算各分箱的占比
        base_counts = pd.cut(base_data, bins=bin_edges).value_counts(normalize=True)
        compare_counts = pd.cut(compare_data, bins=bin_edges).value_counts(normalize=True)
        
        # 对齐索引
        all_bins = base_counts.index.union(compare_counts.index)
        base_pcts = base_counts.reindex(all_bins, fill_value=0.0001)
        compare_pcts = compare_counts.reindex(all_bins, fill_value=0.0001)
        
        # 避免除零和 log(0)
        base_pcts = base_pcts.clip(lower=0.0001)
        compare_pcts = compare_pcts.clip(lower=0.0001)
        
        # 计算 PSI
        bin_psi = (compare_pcts - base_pcts) * np.log(compare_pcts / base_pcts)
        total_psi = bin_psi.sum()
        
        # 构建分箱详情
        bin_details = []
        for bin_label in all_bins:
            bin_details.append({
                'bin': str(bin_label),
                'base_pct': round(float(base_pcts.get(bin_label, 0)), 4),
                'compare_pct': round(float(compare_pcts.get(bin_label, 0)), 4),
                'psi_contribution': round(float(bin_psi.get(bin_label, 0)), 6)
            })
        
        return PSIResult(
            feature=feature_name,
            psi=float(total_psi),
            base_period=base_period,
            compare_period=compare_period,
            bin_details=bin_details
        )
    
    def analyze_feature_stability(
        self,
        data: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
        base_period: Optional[str] = None,
        compare_periods: Optional[List[str]] = None,
        period_column: Optional[str] = None
    ) -> FeatureStabilityReport:
        """
        分析特征随时间的稳定性
        
        Args:
            data: 输入数据
            feature_columns: 要分析的特征列
            base_period: 基准期（如 '202402'）
            compare_periods: 对比期列表
            period_column: 时间周期列名（如果不同于 date_column）
            
        Returns:
            特征稳定性分析报告
        """
        # 确定特征列
        if feature_columns is None:
            feature_columns = [
                c for c in data.select_dtypes(include=[np.number]).columns
                if c != self.date_column and c != period_column
            ]
        
        # 确定时间列
        time_col = period_column or self.date_column
        
        if time_col not in data.columns:
            raise ValueError(f"Time column '{time_col}' not found in data")
        
        # 获取所有时间周期
        all_periods = sorted(data[time_col].unique())
        
        # 确定基准期
        if base_period is None:
            base_period = str(all_periods[0])
        
        # 确定对比期
        if compare_periods is None:
            compare_periods = [str(p) for p in all_periods if str(p) != base_period]
        
        # 获取基准期数据
        base_data = data[data[time_col].astype(str) == str(base_period)]
        
        # 分析每个特征
        feature_timelines = []
        
        for feature in feature_columns:
            timeline = []
            
            for compare_period in compare_periods:
                compare_data = data[data[time_col].astype(str) == str(compare_period)]
                
                if len(compare_data) == 0:
                    continue
                
                psi_result = self.calculate_psi(
                    base_data=base_data[feature],
                    compare_data=compare_data[feature],
                    feature_name=feature,
                    base_period=str(base_period),
                    compare_period=str(compare_period)
                )
                timeline.append(psi_result)
            
            feature_timelines.append(FeatureStabilityTimeline(
                feature=feature,
                timeline=timeline
            ))
        
        return FeatureStabilityReport(
            base_period=str(base_period),
            feature_timelines=feature_timelines
        )
    
    def calculate_monthly_psi(
        self,
        data: pd.DataFrame,
        feature: str,
        month_column: str = 'apply_month'
    ) -> List[Dict[str, Any]]:
        """
        计算特征的逐月 PSI
        
        Args:
            data: 输入数据
            feature: 特征名称
            month_column: 月份列名
            
        Returns:
            逐月 PSI 结果列表
        """
        if month_column not in data.columns:
            raise ValueError(f"Month column '{month_column}' not found")
        
        months = sorted(data[month_column].unique())
        if len(months) < 2:
            return []
        
        base_month = months[0]
        base_data = data[data[month_column] == base_month][feature]
        
        results = []
        for month in months:
            compare_data = data[data[month_column] == month][feature]
            psi_result = self.calculate_psi(
                base_data=base_data,
                compare_data=compare_data,
                feature_name=feature,
                base_period=str(base_month),
                compare_period=str(month)
            )
            results.append({
                'monitor_col': feature,
                'apply_month': month,
                'psi': psi_result.psi,
                'psi_timestamp': str(base_month),
                'psi_neighbor': psi_result.stability_level
            })
        
        return results


# 便捷函数
def calculate_psi(
    base_data: pd.Series,
    compare_data: pd.Series,
    n_bins: int = 10
) -> float:
    """
    便捷函数：计算两个分布之间的 PSI
    
    Args:
        base_data: 基准期数据
        compare_data: 对比期数据
        n_bins: 分箱数量
        
    Returns:
        PSI 值
    """
    analyzer = FeatureStability(n_bins=n_bins)
    result = analyzer.calculate_psi(
        base_data=base_data,
        compare_data=compare_data,
        feature_name="feature"
    )
    return result.psi
