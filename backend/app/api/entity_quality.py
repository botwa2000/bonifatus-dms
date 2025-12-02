# backend/app/api/entity_quality.py
"""
Bonifatus DMS - Entity Quality ML API Endpoints
ML model training, statistics, and management for entity quality scoring
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.database.connection import db_manager
from app.api.auth import get_current_active_user
from app.database.models import User, EntityQualityModel, EntityQualityTrainingData, SupportedLanguage
from app.services.entity_ml_service import get_entity_ml_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entity-quality", tags=["entity-quality"])


# ==================== Request/Response Models ====================


class RetrainRequest(BaseModel):
    """Request to retrain ML model"""
    language: Optional[str] = Field(None, description="Language code (de/en/fr/ru) or None for all")
    model_type: str = Field("logistic", description="Model type: 'logistic' or 'random_forest'")
    sync_blacklist: bool = Field(True, description="Sync entity_blacklist to training data before training")


class RetrainResponse(BaseModel):
    """Response from retrain request"""
    success: bool
    message: str
    models_trained: Dict[str, Optional[str]]  # language -> model_version
    training_stats: Dict[str, Dict[str, int]]  # language -> {valid, invalid, total}


class SyncBlacklistRequest(BaseModel):
    """Request to sync blacklist to training data"""
    language: Optional[str] = Field(None, description="Language code or None for all")


class SyncBlacklistResponse(BaseModel):
    """Response from sync blacklist request"""
    success: bool
    message: str
    synced_count: int


class TrainingStatsResponse(BaseModel):
    """Training data statistics"""
    stats: Dict[str, Dict[str, int]]  # language -> {valid, invalid, total}


class ModelInfo(BaseModel):
    """ML model information"""
    model_version: str
    language: str
    model_type: str
    is_active: bool
    training_samples_count: int
    performance_metrics: Dict[str, float]
    created_at: str


class ModelsListResponse(BaseModel):
    """List of all trained models"""
    models: List[ModelInfo]


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str


# ==================== Endpoints ====================


@router.post(
    "/retrain",
    response_model=RetrainResponse,
    responses={
        200: {"model": RetrainResponse, "description": "Models retrained successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def retrain_models(
    request: RetrainRequest,
    current_user: User = Depends(get_current_active_user)
) -> RetrainResponse:
    """
    Retrain ML models for entity quality scoring

    Requires admin privileges. Trains new models based on accumulated training data.
    Can train for specific language or all languages.

    Minimum requirements per language:
    - 100 total training samples
    - At least 10 valid AND 10 invalid examples

    Returns model versions and training statistics.
    """
    # Check admin privileges
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for model retraining"
        )

    session = db_manager.session_local()

    try:
        ml_service = get_entity_ml_service(session)

        # Sync blacklist if requested
        if request.sync_blacklist:
            sync_count = ml_service.sync_blacklist_to_training_data(language=request.language)
            logger.info(f"Synced {sync_count} blacklist entries to training data")

        # Determine which languages to train
        if request.language:
            # Train specific language
            languages_to_train = [request.language]
        else:
            # Train all active languages
            supported_langs = session.query(SupportedLanguage).filter(
                SupportedLanguage.is_active == True
            ).all()
            languages_to_train = [lang.language_code for lang in supported_langs]

        # Train models
        models_trained = {}
        for lang in languages_to_train:
            try:
                model_version = ml_service.train_model(
                    language=lang,
                    model_type=request.model_type,
                    test_size=0.2
                )
                models_trained[lang] = model_version

                if model_version:
                    logger.info(f"Successfully trained model {model_version} for {lang}")
                else:
                    logger.warning(f"Failed to train model for {lang} (insufficient data?)")

            except Exception as e:
                logger.error(f"Error training model for {lang}: {e}")
                models_trained[lang] = None

        # Get updated training stats
        training_stats = ml_service.get_training_stats()

        # Determine success
        success = any(v is not None for v in models_trained.values())

        if success:
            message = f"Successfully trained models for {sum(1 for v in models_trained.values() if v)} languages"
        else:
            message = "No models trained - insufficient training data for all languages"

        return RetrainResponse(
            success=success,
            message=message,
            models_trained=models_trained,
            training_stats=training_stats
        )

    except Exception as e:
        logger.error(f"Error in retrain_models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrain models: {str(e)}"
        )
    finally:
        session.close()


@router.post(
    "/sync-blacklist",
    response_model=SyncBlacklistResponse,
    responses={
        200: {"model": SyncBlacklistResponse, "description": "Blacklist synced successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def sync_blacklist(
    request: SyncBlacklistRequest,
    current_user: User = Depends(get_current_active_user)
) -> SyncBlacklistResponse:
    """
    Sync entity_blacklist entries to training data

    Adds blacklisted entities as negative training examples.
    Extracts features and stores in entity_quality_training_data table.

    Can sync for specific language or all languages.
    """
    # Check admin privileges
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for blacklist sync"
        )

    session = db_manager.session_local()

    try:
        ml_service = get_entity_ml_service(session)

        synced_count = ml_service.sync_blacklist_to_training_data(language=request.language)

        return SyncBlacklistResponse(
            success=True,
            message=f"Synced {synced_count} blacklist entries to training data",
            synced_count=synced_count
        )

    except Exception as e:
        logger.error(f"Error syncing blacklist: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync blacklist: {str(e)}"
        )
    finally:
        session.close()


@router.get(
    "/stats",
    response_model=TrainingStatsResponse,
    responses={
        200: {"model": TrainingStatsResponse, "description": "Training statistics"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_training_stats(
    current_user: User = Depends(get_current_active_user)
) -> TrainingStatsResponse:
    """
    Get training data statistics

    Returns count of valid/invalid training examples per language.
    Useful for determining if enough data exists to train models.
    """
    # Check admin privileges
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to view training stats"
        )

    session = db_manager.session_local()

    try:
        ml_service = get_entity_ml_service(session)
        stats = ml_service.get_training_stats()

        return TrainingStatsResponse(stats=stats)

    except Exception as e:
        logger.error(f"Error getting training stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get training stats: {str(e)}"
        )
    finally:
        session.close()


@router.get(
    "/models",
    response_model=ModelsListResponse,
    responses={
        200: {"model": ModelsListResponse, "description": "List of trained models"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_models(
    current_user: User = Depends(get_current_active_user)
) -> ModelsListResponse:
    """
    List all trained ML models

    Returns information about all entity quality models including:
    - Model version and type
    - Training performance metrics
    - Active status
    - Language
    """
    # Check admin privileges
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to view models"
        )

    session = db_manager.session_local()

    try:
        models = session.query(EntityQualityModel).order_by(
            EntityQualityModel.language,
            EntityQualityModel.created_at.desc()
        ).all()

        model_info_list = [
            ModelInfo(
                model_version=model.model_version,
                language=model.language,
                model_type=model.model_type,
                is_active=model.is_active,
                training_samples_count=model.training_samples_count or 0,
                performance_metrics=model.performance_metrics or {},
                created_at=model.created_at.isoformat() if model.created_at else ""
            )
            for model in models
        ]

        return ModelsListResponse(models=model_info_list)

    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )
    finally:
        session.close()
