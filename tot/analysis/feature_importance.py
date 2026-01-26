"""
FeatureImportance - 特征重要性分析

功能：
- 计算特征 IV (Information Value) 值
- 计算模型特征重要性（基于树模型的 feature_importances_）
- 支持特征重要性排序和筛选
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from collections import OrderedDict
import warnings


@dataclass
class IVResult:
    """单个特征的 IV 计算结果"""
    feature: str
    iv: float
    woe_bins: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def iv_strength(self) -> str:
        """IV 强度评级"""
        if self.iv < 0.02:
            return "无预测力"
        elif self.iv < 0.1:
            return "弱预测力"
        elif self.iv < 0.3:
            return "中等预测力"
        elif self.iv < 0.5:
            return "强预测力"
        else:
            return "过强(可能过拟合)"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'feature': self.feature,
            'iv': self.iv,
            'iv_strength': self.iv_strength,
            'woe_bins': self.woe_bins
        }


@dataclass  
class ModelImportanceResult:
    """模型特征重要性结果"""
    feature: str
    importance: float           # 重要性分数
    importance_pct: float       # 重要性百分比
    cumulative_pct: float       # 累计百分比
    rank: int                   # 排名
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'feature': self.feature,
            'importance': round(self.importance, 4),
            'importance_pct': f"{self.importance_pct:.2%}",
            'cumulative_pct': f"{self.cumulative_pct:.2%}",
            'rank': self.rank
        }


@dataclass
class FeatureImportanceReport:
    """特征重要性分析报告"""
    iv_results: List[IVResult] = field(default_factory=list)
    model_importance: List[ModelImportanceResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'iv_results': [r.to_dict() for r in self.iv_results],
            'model_importance': [r.to_dict() for r in self.model_importance]
        }
    
    def get_top_iv_features(self, n: int = 10) -> List[IVResult]:
        """获取 IV 值前 N 的特征"""
        return sorted(self.iv_results, key=lambda x: x.iv, reverse=True)[:n]
    
    def get_top_model_features(self, n: int = 10) -> List[ModelImportanceResult]:
        """获取模型重要性前 N 的特征"""
        return sorted(self.model_importance, key=lambda x: x.importance, reverse=True)[:n]
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "## 特征重要性分析",
            ""
        ]
        
        # IV 分析结果
        if self.iv_results:
            lines.extend([
                "### 特征 IV 值分析",
                "",
                "| 排名 | 特征名 | IV 值 | 预测力评级 |",
                "|------|--------|-------|------------|"
            ])
            top_iv = self.get_top_iv_features(20)
            for i, result in enumerate(top_iv, 1):
                lines.append(
                    f"| {i} | {result.feature} | {result.iv:.6f} | {result.iv_strength} |"
                )
            lines.append("")
        
        # 模型重要性结果
        if self.model_importance:
            lines.extend([
                "### 模型特征重要性",
                "",
                "| 排名 | 特征名 | 重要性分数 | 占比 | 累计占比 |",
                "|------|--------|------------|------|----------|"
            ])
            top_model = self.get_top_model_features(20)
            for result in top_model:
                lines.append(
                    f"| {result.rank} | {result.feature} | {result.importance:.4f} | "
                    f"{result.importance_pct:.2%} | {result.cumulative_pct:.2%} |"
                )
            lines.append("")
        
        return "\n".join(lines)


class FeatureImportance:
    """特征重要性分析器"""
    
    def __init__(
        self,
        label_column: str = 'default_flag',
        n_bins: int = 10,
        min_samples_per_bin: int = 50
    ):
        """
        初始化特征重要性分析器
        
        Args:
            label_column: 标签列名
            n_bins: WOE 分箱数量
            min_samples_per_bin: 每个分箱最小样本数
        """
        self.label_column = label_column
        self.n_bins = n_bins
        self.min_samples_per_bin = min_samples_per_bin
    
    def calculate_iv(
        self,
        data: pd.DataFrame,
        feature_columns: Optional[List[str]] = None
    ) -> List[IVResult]:
        """
        计算特征的 IV 值
        
        Args:
            data: 输入数据
            feature_columns: 要计算的特征列，默认为所有数值列
            
        Returns:
            IV 计算结果列表
        """
        if self.label_column not in data.columns:
            raise ValueError(f"Label column '{self.label_column}' not found in data")
        
        if feature_columns is None:
            feature_columns = [
                c for c in data.select_dtypes(include=[np.number]).columns
                if c != self.label_column
            ]
        
        results = []
        for col in feature_columns:
            try:
                iv_result = self._calculate_single_iv(data, col)
                results.append(iv_result)
            except Exception as e:
                warnings.warn(f"Failed to calculate IV for {col}: {e}")
                results.append(IVResult(feature=col, iv=0.0))
        
        # 按 IV 值降序排序
        results.sort(key=lambda x: x.iv, reverse=True)
        return results
    
    def _calculate_single_iv(self, data: pd.DataFrame, feature: str) -> IVResult:
        """计算单个特征的 IV 值"""
        df = data[[feature, self.label_column]].dropna()
        
        if len(df) < self.min_samples_per_bin * 2:
            return IVResult(feature=feature, iv=0.0)
        
        # 分箱
        try:
            df['bin'] = pd.qcut(df[feature], q=self.n_bins, duplicates='drop')
        except ValueError:
            # 如果无法等频分箱，尝试等宽分箱
            df['bin'] = pd.cut(df[feature], bins=self.n_bins, duplicates='drop')
        
        # 计算每个分箱的 WOE 和 IV
        total_good = (df[self.label_column] == 0).sum()
        total_bad = (df[self.label_column] == 1).sum()
        
        if total_good == 0 or total_bad == 0:
            return IVResult(feature=feature, iv=0.0)
        
        woe_bins = []
        total_iv = 0.0
        
        for bin_label, group in df.groupby('bin', observed=True):
            good_count = (group[self.label_column] == 0).sum()
            bad_count = (group[self.label_column] == 1).sum()
            
            # 避免除零
            good_pct = max(good_count / total_good, 0.0001)
            bad_pct = max(bad_count / total_bad, 0.0001)
            
            woe = np.log(bad_pct / good_pct)
            iv = (bad_pct - good_pct) * woe
            
            total_iv += iv
            
            woe_bins.append({
                'bin': str(bin_label),
                'count': len(group),
                'good_count': int(good_count),
                'bad_count': int(bad_count),
                'woe': round(woe, 4),
                'iv': round(iv, 6)
            })
        
        return IVResult(
            feature=feature,
            iv=total_iv,
            woe_bins=woe_bins
        )
    
    def calculate_model_importance(
        self,
        model: Any,
        feature_names: List[str]
    ) -> List[ModelImportanceResult]:
        """
        从训练好的模型中提取特征重要性
        
        Args:
            model: 训练好的模型（需要有 feature_importances_ 属性）
            feature_names: 特征名称列表
            
        Returns:
            模型特征重要性结果列表
        """
        if not hasattr(model, 'feature_importances_'):
            raise ValueError("Model does not have feature_importances_ attribute")
        
        importances = model.feature_importances_
        
        if len(importances) != len(feature_names):
            raise ValueError(
                f"Length mismatch: {len(importances)} importances vs "
                f"{len(feature_names)} feature names"
            )
        
        # 创建排序后的结果
        total_importance = sum(importances)
        importance_pairs = list(zip(feature_names, importances))
        importance_pairs.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        cumulative_pct = 0.0
        
        for rank, (feature, importance) in enumerate(importance_pairs, 1):
            importance_pct = importance / total_importance if total_importance > 0 else 0
            cumulative_pct += importance_pct
            
            results.append(ModelImportanceResult(
                feature=feature,
                importance=importance,
                importance_pct=importance_pct,
                cumulative_pct=cumulative_pct,
                rank=rank
            ))
        
        return results
    
    def analyze(
        self,
        data: pd.DataFrame,
        model: Any = None,
        feature_columns: Optional[List[str]] = None
    ) -> FeatureImportanceReport:
        """
        执行完整的特征重要性分析
        
        Args:
            data: 输入数据
            model: 可选的训练好的模型
            feature_columns: 要分析的特征列
            
        Returns:
            特征重要性分析报告
        """
        report = FeatureImportanceReport()
        
        # 计算 IV
        iv_results = self.calculate_iv(data, feature_columns)
        report.iv_results = iv_results
        
        # 如果提供了模型，计算模型重要性
        if model is not None:
            if feature_columns is None:
                feature_columns = [
                    c for c in data.select_dtypes(include=[np.number]).columns
                    if c != self.label_column
                ]
            model_importance = self.calculate_model_importance(model, feature_columns)
            report.model_importance = model_importance
        
        return report


# 便捷函数
def calculate_feature_iv(
    data: pd.DataFrame,
    label_column: str = 'default_flag',
    feature_columns: Optional[List[str]] = None,
    n_bins: int = 10
) -> List[IVResult]:
    """
    便捷函数：计算特征 IV 值
    
    Args:
        data: 输入数据
        label_column: 标签列名
        feature_columns: 特征列
        n_bins: 分箱数量
        
    Returns:
        IV 计算结果列表
    """
    analyzer = FeatureImportance(label_column=label_column, n_bins=n_bins)
    return analyzer.calculate_iv(data, feature_columns)
