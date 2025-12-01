from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.sql import func
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
