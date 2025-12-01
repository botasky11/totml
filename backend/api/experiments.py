import asyncio
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pathlib import Path
import logging

from backend.database import get_db
from backend.schemas import ExperimentCreate, ExperimentUpdate, ExperimentResponse, NodeResponse
from backend.services.experiment_service import ExperimentService
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
    
    # Run experiment in background
    async def websocket_callback(message):
        if experiment_id in active_connections:
            try:
                await active_connections[experiment_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
    
    asyncio.create_task(service.run_experiment_async(experiment_id, websocket_callback))
    
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


@router.websocket("/ws/{experiment_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    experiment_id: str,
):
    """WebSocket endpoint for real-time experiment updates"""
    await websocket.accept()
    active_connections[experiment_id] = websocket
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for experiment {experiment_id}")
        if experiment_id in active_connections:
            del active_connections[experiment_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if experiment_id in active_connections:
            del active_connections[experiment_id]
