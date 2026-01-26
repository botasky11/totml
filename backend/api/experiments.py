import asyncio
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pathlib import Path
import logging

from backend.database import get_db
from backend.schemas import (
    ExperimentCreate, ExperimentUpdate, ExperimentResponse, 
    NodeResponse, ExperimentStatus, FeatureAnalysisReportResponse
)
from backend.services.experiment_service import ExperimentService
from backend.services.feature_analysis_service import FeatureAnalysisService
from backend.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Store active WebSocket connections
active_connections: dict[str, WebSocket] = {}


@router.post("/", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    experiment: ExperimentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new experiment"""
    # Create temporary data directory
    data_dir = Path(settings.UPLOAD_DIR) / f"exp_{experiment.name.replace(' ', '_')}"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    service = ExperimentService(db)
    db_experiment = await service.create_experiment(
        experiment_data=experiment,
        data_dir=str(data_dir)
    )
    
    return db_experiment


@router.get("/", response_model=List[ExperimentResponse])
async def list_experiments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all experiments"""
    service = ExperimentService(db)
    experiments = await service.list_experiments(skip=skip, limit=limit)
    return experiments


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific experiment"""
    service = ExperimentService(db)
    experiment = await service.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return experiment


@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str,
    update_data: ExperimentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an experiment"""
    service = ExperimentService(db)
    experiment = await service.update_experiment(experiment_id, update_data)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return experiment


@router.delete("/{experiment_id}", status_code=204)
async def delete_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an experiment"""
    service = ExperimentService(db)
    success = await service.delete_experiment(experiment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return None


@router.post("/{experiment_id}/upload")
async def upload_files(
    experiment_id: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload data files for an experiment"""
    service = ExperimentService(db)
    experiment = await service.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    data_dir = Path(experiment.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_files = []
    for file in files:
        file_path = data_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded_files.append(file.filename)
    
    return {"uploaded_files": uploaded_files}


@router.post("/{experiment_id}/run")
async def run_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Start running an experiment"""
    service = ExperimentService(db)
    experiment = await service.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if experiment.status == "running":
        raise HTTPException(status_code=400, detail="Experiment is already running")
    
    # Run experiment in background with independent session
    async def run_background_task():
        from backend.database.base import async_session_maker

        async def websocket_callback(message):
            logger.info(f"[WS_CALLBACK] Attempting to send message for experiment {experiment_id}, type: {message.get('type')}")
            logger.info(f"[WS_CALLBACK] Active connections: {list(active_connections.keys())}")

            if experiment_id in active_connections:
                try:
                    await active_connections[experiment_id].send_json(message)
                    logger.info(f"[WS_CALLBACK] Successfully sent {message.get('type')} message to experiment {experiment_id}")
                except Exception as e:
                    logger.error(f"[WS_CALLBACK] Error sending WebSocket message for experiment {experiment_id}: {e}", exc_info=True)
            else:
                logger.warning(f"[WS_CALLBACK] No active WebSocket connection for experiment {experiment_id}. Message type: {message.get('type')}")
        
        # Create independent database session for background task
        async with async_session_maker() as bg_db:
            try:
                bg_service = ExperimentService(bg_db)
                await bg_service.run_experiment_async(experiment_id, websocket_callback)
            except Exception as e:
                logger.error(f"Background task error: {e}")
                # Try to update experiment status to failed
                try:
                    await bg_service.update_experiment(
                        experiment_id,
                        ExperimentUpdate(status=ExperimentStatus.FAILED, error_message=str(e))
                    )
                except Exception:
                    logger.error(f"Failed to update experiment status to FAILED for experiment {experiment_id}")
                    pass
    
    asyncio.create_task(run_background_task())
    
    return {"message": "Experiment started", "experiment_id": experiment_id}


@router.get("/{experiment_id}/nodes", response_model=List[NodeResponse])
async def get_experiment_nodes(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all nodes for an experiment"""
    service = ExperimentService(db)
    nodes = await service.get_experiment_nodes(experiment_id)
    return nodes


@router.get("/{experiment_id}/analysis", response_model=FeatureAnalysisReportResponse)
async def get_feature_analysis_report(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get feature analysis report for an experiment"""
    service = FeatureAnalysisService(db)
    report = await service.get_report_by_experiment(experiment_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Feature analysis report not found")
    
    return report


@router.post("/{experiment_id}/analysis", response_model=FeatureAnalysisReportResponse)
async def generate_feature_analysis_report(
    experiment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate or regenerate feature analysis report for an experiment.
    
    This endpoint can be used to:
    1. Generate a report for experiments that completed before this feature was added
    2. Regenerate a report with updated analysis
    
    Note: The experiment must be in COMPLETED status.
    """
    # First check if experiment exists and is completed
    exp_service = ExperimentService(db)
    experiment = await exp_service.get_experiment(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if experiment.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Experiment must be completed to generate analysis report (current status: {experiment.status})"
        )
    
    # Generate the report
    service = FeatureAnalysisService(db)
    try:
        report = await service.generate_analysis_report(experiment_id)
        return report
    except Exception as e:
        logger.error(f"Failed to generate analysis report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis report: {str(e)}")


@router.websocket("/ws/{experiment_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    experiment_id: str,
):
    """WebSocket endpoint for real-time experiment updates"""
    logger.info(f"[WS] New WebSocket connection request for experiment {experiment_id}")

    try:
        await websocket.accept()
        logger.info(f"[WS] WebSocket connection accepted for experiment {experiment_id}")

        active_connections[experiment_id] = websocket
        logger.info(f"[WS] Added to active_connections. Total connections: {len(active_connections)}")

        # Send initial connection confirmation
        try:
            await websocket.send_json({
                "type": "connection_established",
                "data": {
                    "experiment_id": experiment_id,
                    "timestamp": datetime.now().isoformat()
                }
            })
            logger.info(f"[WS] Sent connection_established message to experiment {experiment_id}")
        except Exception as send_error:
            logger.warning(f"[WS] Failed to send connection_established (client likely disconnected): {send_error}")
            # 清理连接并退出
            if experiment_id in active_connections:
                del active_connections[experiment_id]
            return

        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            logger.debug(f"[WS] Received message from client for experiment {experiment_id}: {data}")
    except WebSocketDisconnect:
        logger.info(f"[WS] WebSocket disconnected for experiment {experiment_id}")
        if experiment_id in active_connections:
            del active_connections[experiment_id]
            logger.info(f"[WS] Removed from active_connections. Remaining connections: {len(active_connections)}")
    except Exception as e:
        logger.error(f"[WS] WebSocket error for experiment {experiment_id}: {e}", exc_info=True)
        if experiment_id in active_connections:
            del active_connections[experiment_id]
            logger.info(f"[WS] Removed from active_connections due to error. Remaining: {len(active_connections)}")
