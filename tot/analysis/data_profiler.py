"""
DataProfiler - 建模前样本数据统计

功能：
- 数据文件基础统计：样本数据量、特征数据量、正负样本比例
- 按数据集分组的样本情况统计
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class DatasetStats:
    """数据集统计结果"""
    name: str                    # 数据集名称 (train/valid/oot/all)
    cnt: int                     # 样本总数
    blk_cnt: int                 # 正样本数量 (default_flag=1)
    blk_rate: float              # 正样本比例
    dt_min: str                  # 最早日期
    dt_max: str                  # 最晚日期
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'cnt': self.cnt,
            'blk_cnt': self.blk_cnt,
            'blk_rate': f"{self.blk_rate:.3%}",
            'dt_min': self.dt_min,
            'dt_max': self.dt_max
        }


@dataclass
class DataProfileResult:
    """数据概况统计结果"""
    file_name: str               # 文件名
    sample_count: int            # 样本数据量
    feature_count: int           # 特征数据量
    majority_class_count: int    # 多数类数量
    minority_class_count: int    # 少数类数量
    label_column: str            # 标签列名
    dataset_column: Optional[str] = None  # 数据集划分列名
    date_column: Optional[str] = None     # 日期列名
    dataset_stats: List[DatasetStats] = field(default_factory=list)
    feature_dtypes: Dict[str, str] = field(default_factory=dict)
    missing_stats: Dict[str, float] = field(default_factory=dict)
    
    @property
    def majority_minority_ratio(self) -> str:
        return f"多数类 {self.majority_class_count} / 少数类 {self.minority_class_count}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_name': self.file_name,
            'sample_count': self.sample_count,
            'feature_count': self.feature_count,
            'majority_class_count': self.majority_class_count,
            'minority_class_count': self.minority_class_count,
            'majority_minority_ratio': self.majority_minority_ratio,
            'label_column': self.label_column,
            'dataset_column': self.dataset_column,
            'date_column': self.date_column,
            'dataset_stats': [s.to_dict() for s in self.dataset_stats],
            'feature_dtypes': self.feature_dtypes,
            'missing_stats': self.missing_stats
        }
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "## 样本数据统计",
            "",
            "### 基础信息",
            "",
            f"- **数据文件**: {self.file_name}",
            f"- **样本数据量**: {self.sample_count:,}",
            f"- **特征数据量**: {self.feature_count}",
            f"- **正负样本比例**: {self.majority_minority_ratio}",
            "",
        ]
        
        if self.dataset_stats:
            lines.extend([
                "### 按数据集分组的样本情况",
                "",
                "| 数据集 | 样本数 | 正样本数 | 正样本率 | 开始日期 | 结束日期 |",
                "|--------|--------|----------|----------|----------|----------|"
            ])
            for stat in self.dataset_stats:
                lines.append(
                    f"| {stat.name} | {stat.cnt:,} | {stat.blk_cnt:,} | "
                    f"{stat.blk_rate:.3%} | {stat.dt_min} | {stat.dt_max} |"
                )
            lines.append("")
        
        return "\n".join(lines)


class DataProfiler:
    """建模前样本数据统计器"""
    
    def __init__(
        self,
        label_column: str = 'default_flag',
        dataset_column: Optional[str] = 'dataset',
        date_column: Optional[str] = 'dt',
        positive_label: int = 1
    ):
        """
        初始化数据概况统计器
        
        Args:
            label_column: 标签列名，默认 'default_flag'
            dataset_column: 数据集划分列名，默认 'dataset'
            date_column: 日期列名，默认 'dt'
            positive_label: 正样本标签值，默认 1
        """
        self.label_column = label_column
        self.dataset_column = dataset_column
        self.date_column = date_column
        self.positive_label = positive_label
    
    def profile(self, data: pd.DataFrame, file_name: str = "data.csv") -> DataProfileResult:
        """
        执行数据概况统计
        
        Args:
            data: 输入数据 DataFrame
            file_name: 数据文件名
            
        Returns:
            DataProfileResult 统计结果对象
        """
        # 基础统计
        sample_count = len(data)
        
        # 特征数量（排除标签列、数据集列、日期列）
        exclude_cols = {self.label_column}
        if self.dataset_column and self.dataset_column in data.columns:
            exclude_cols.add(self.dataset_column)
        if self.date_column and self.date_column in data.columns:
            exclude_cols.add(self.date_column)
        
        feature_columns = [c for c in data.columns if c not in exclude_cols]
        feature_count = len(feature_columns)
        
        # 正负样本统计
        if self.label_column in data.columns:
            label_counts = data[self.label_column].value_counts()
            positive_count = label_counts.get(self.positive_label, 0)
            negative_count = sample_count - positive_count
            
            if positive_count > negative_count:
                majority_count = positive_count
                minority_count = negative_count
            else:
                majority_count = negative_count
                minority_count = positive_count
        else:
            majority_count = sample_count
            minority_count = 0
        
        # 特征数据类型
        feature_dtypes = {col: str(data[col].dtype) for col in feature_columns}
        
        # 缺失率统计
        missing_stats = {
            col: data[col].isna().mean() 
            for col in feature_columns
        }
        
        # 按数据集分组统计
        dataset_stats = self._compute_dataset_stats(data)
        
        return DataProfileResult(
            file_name=file_name,
            sample_count=sample_count,
            feature_count=feature_count,
            majority_class_count=majority_count,
            minority_class_count=minority_count,
            label_column=self.label_column,
            dataset_column=self.dataset_column,
            date_column=self.date_column,
            dataset_stats=dataset_stats,
            feature_dtypes=feature_dtypes,
            missing_stats=missing_stats
        )
    
    def _compute_dataset_stats(self, data: pd.DataFrame) -> List[DatasetStats]:
        """计算按数据集分组的统计"""
        stats = []
        
        # 检查必要的列是否存在
        has_dataset = self.dataset_column and self.dataset_column in data.columns
        has_label = self.label_column in data.columns
        has_date = self.date_column and self.date_column in data.columns
        
        if not has_label:
            return stats
        
        def compute_group_stats(group_data: pd.DataFrame, name: str) -> DatasetStats:
            cnt = len(group_data)
            blk_cnt = (group_data[self.label_column] == self.positive_label).sum()
            blk_rate = blk_cnt / cnt if cnt > 0 else 0.0
            
            if has_date:
                dt_col = group_data[self.date_column]
                # 处理日期格式
                if pd.api.types.is_numeric_dtype(dt_col):
                    dt_min = str(int(dt_col.min()))
                    dt_max = str(int(dt_col.max()))
                else:
                    dt_min = str(dt_col.min())
                    dt_max = str(dt_col.max())
            else:
                dt_min = "N/A"
                dt_max = "N/A"
            
            return DatasetStats(
                name=name,
                cnt=cnt,
                blk_cnt=int(blk_cnt),
                blk_rate=blk_rate,
                dt_min=dt_min,
                dt_max=dt_max
            )
        
        # 按数据集分组统计
        if has_dataset:
            # 定义排序顺序
            order = ['train', 'valid', 'oot', 'test']
            groups = data.groupby(self.dataset_column)
            
            # 按预定义顺序排序
            sorted_groups = sorted(
                groups,
                key=lambda x: order.index(x[0]) if x[0] in order else len(order)
            )
            
            for name, group_data in sorted_groups:
                stats.append(compute_group_stats(group_data, str(name)))
        
        # 添加总体统计
        stats.append(compute_group_stats(data, 'all'))
        
        return stats
    
    def profile_from_file(self, file_path: str) -> DataProfileResult:
        """
        从文件加载数据并执行统计
        
        Args:
            file_path: 数据文件路径
            
        Returns:
            DataProfileResult 统计结果对象
        """
        path = Path(file_path)
        
        if path.suffix.lower() == '.csv':
            data = pd.read_csv(file_path)
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            data = pd.read_excel(file_path)
        elif path.suffix.lower() == '.parquet':
            data = pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        return self.profile(data, path.name)


# 便捷函数
def profile_data(
    data: pd.DataFrame,
    label_column: str = 'default_flag',
    dataset_column: Optional[str] = 'dataset',
    date_column: Optional[str] = 'dt',
    file_name: str = "data.csv"
) -> DataProfileResult:
    """
    便捷函数：执行数据概况统计
    
    Args:
        data: 输入数据 DataFrame
        label_column: 标签列名
        dataset_column: 数据集划分列名
        date_column: 日期列名
        file_name: 数据文件名
        
    Returns:
        DataProfileResult 统计结果对象
    """
    profiler = DataProfiler(
        label_column=label_column,
        dataset_column=dataset_column,
        date_column=date_column
    )
    return profiler.profile(data, file_name)
