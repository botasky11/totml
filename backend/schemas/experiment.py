from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    goal: str = Field(..., min_length=1)
    eval_metric: str = Field(..., min_length=1)
    num_steps: int = Field(default=20, ge=1, le=100)
    model_name: Optional[str] = "gpt-4-turbo"
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "House Price Prediction",
                "description": "Predict sales prices using the provided dataset",
                "goal": "Predict the sales price for each house",
                "eval_metric": "RMSE between log-prices",
                "num_steps": 20,
                "model_name": "gpt-4-turbo"
            }
        }


class ExperimentUpdate(BaseModel):
    status: Optional[ExperimentStatus] = None
    current_step: Optional[int] = None
    progress: Optional[float] = None
    best_metric_value: Optional[float] = None
    best_solution_code: Optional[str] = None
    error_message: Optional[str] = None
    journal_data: Optional[Any] = None


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    goal: str
    eval_metric: str
    num_steps: int
    model_name: Optional[str]
    status: str
    current_step: int
    progress: float
    best_metric_value: Optional[float]
    best_solution_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    config: Optional[Any]
    journal_data: Optional[Any]
    
    class Config:
        from_attributes = True


class NodeCreate(BaseModel):
    experiment_id: str
    step: int
    parent_id: Optional[str] = None
    plan: Optional[str] = None
    code: str
    metric_value: Optional[float] = None
    is_buggy: bool = False
    term_out: Optional[str] = None
    analysis: Optional[str] = None


class NodeResponse(BaseModel):
    id: str
    experiment_id: str
    step: int
    parent_id: Optional[str]
    plan: Optional[str]
    code: str
    metric_value: Optional[float]
    is_buggy: bool
    term_out: Optional[str]
    analysis: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    type: str  # status_update, log, error, complete
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)
