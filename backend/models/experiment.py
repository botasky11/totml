from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database.base import Base
import uuid


class Experiment(Base):
    __tablename__ = "experiments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Task configuration
    goal = Column(Text, nullable=False)
    eval_metric = Column(String(100), nullable=False)
    data_dir = Column(String(512))
    
    # Execution parameters
    num_steps = Column(Integer, default=20)
    model_name = Column(String(100))
    
    # Status
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    current_step = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    
    # Results
    best_metric_value = Column(Float)
    best_solution_code = Column(Text)
    error_message = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Additional data
    config = Column(JSON)
    journal_data = Column(JSON)


class ExperimentNode(Base):
    __tablename__ = "experiment_nodes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), nullable=False, index=True)
    
    # Node information
    step = Column(Integer, nullable=False)
    parent_id = Column(String(36))
    
    # Code and plan
    plan = Column(Text)
    code = Column(Text, nullable=False)
    
    # Execution results
    metric_value = Column(Float)
    is_buggy = Column(Boolean, default=False)
    term_out = Column(Text)
    analysis = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FeatureAnalysisReport(Base):
    """特征分析报告表 - 存储实验完成后的完整分析报告"""
    __tablename__ = "feature_analysis_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String(36), ForeignKey("experiments.id"), nullable=False, unique=True, index=True)
    best_node_id = Column(String(36), ForeignKey("experiment_nodes.id"), nullable=True)
    
    # 数据概况统计 (建模前)
    data_profile = Column(JSON)  # DataProfileResult.to_dict()
    
    # 特征分析 (建模后)
    feature_importance = Column(JSON)  # FeatureImportanceReport.to_dict()
    feature_stability = Column(JSON)   # FeatureStabilityReport.to_dict()
    
    # 模型分析 (建模后)
    model_stability = Column(JSON)     # ModelStabilityResult.to_dict()
    model_evaluation = Column(JSON)    # ModelEvaluationReport.to_dict()
    
    # 特征统计指标
    feature_statistics = Column(JSON)  # List[FeatureStatistics.to_dict()]
    
    # 完整报告
    full_report_md = Column(Text)      # Markdown 格式的完整报告
    
    # 分析元数据
    analysis_config = Column(JSON)     # 分析配置参数
    error_message = Column(Text)       # 分析过程中的错误信息
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
