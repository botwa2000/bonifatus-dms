"""
Entity ML Service for Bonifatus DMS
Handles ML model training, prediction, and feedback loop for entity quality scoring
Uses sklearn for industry-standard machine learning
"""

import logging
import joblib
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)


class EntityMLService:
    """Service for ML-based entity quality scoring"""

    def __init__(self, db: Session):
        """
        Initialize ML service with database session

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def collect_training_data(self, language: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Collect training data from entity_quality_training_data table

        Args:
            language: Language code (de, en, fr, ru)

        Returns:
            Tuple of (X, y) where X is feature matrix and y is labels
        """
        try:
            from app.database.models import EntityQualityTrainingData

            # Query training data for language
            training_data = self.db.query(EntityQualityTrainingData).filter(
                EntityQualityTrainingData.language == language
            ).all()

            if not training_data:
                logger.warning(f"No training data found for language: {language}")
                return np.array([]), np.array([])

            # Extract features and labels
            X_list = []
            y_list = []

            for data in training_data:
                if data.features:  # JSONB features column
                    # Convert JSONB features to ordered array
                    features_dict = data.features
                    feature_vector = self._dict_to_feature_vector(features_dict)
                    X_list.append(feature_vector)
                    y_list.append(1 if data.is_valid else 0)

            if not X_list:
                logger.warning(f"No valid features found in training data for {language}")
                return np.array([]), np.array([])

            X = np.array(X_list)
            y = np.array(y_list)

            logger.info(f"Collected {len(y)} training samples for {language} (valid={sum(y)}, invalid={len(y)-sum(y)})")
            return X, y

        except Exception as e:
            logger.error(f"Failed to collect training data for {language}: {e}")
            return np.array([]), np.array([])

    def _dict_to_feature_vector(self, features: Dict[str, float]) -> List[float]:
        """
        Convert features dictionary to ordered feature vector

        Args:
            features: Dictionary of feature names to values

        Returns:
            List of feature values in consistent order
        """
        # Define consistent feature order (must match extraction order)
        feature_names = [
            'length', 'word_count', 'vowel_ratio', 'consonant_ratio',
            'digit_ratio', 'special_char_ratio', 'repetitive_char_score',
            'dict_valid_ratio', 'stop_word_ratio', 'has_field_label_suffix',
            'title_case', 'spacy_confidence',
            'is_person', 'is_organization', 'is_location'
        ]

        return [features.get(name, 0.0) for name in feature_names]

    def train_model(
        self,
        language: str,
        model_type: str = 'logistic',
        test_size: float = 0.2
    ) -> Optional[str]:
        """
        Train ML model for entity quality scoring

        Args:
            language: Language code
            model_type: 'logistic' or 'random_forest'
            test_size: Proportion of data for testing

        Returns:
            Model version string if successful, None otherwise
        """
        try:
            # Collect training data
            X, y = self.collect_training_data(language)

            if len(X) == 0:
                logger.error(f"No training data available for {language}")
                return None

            # Check minimum samples from config
            from app.database.models import EntityQualityConfig
            config = self.db.query(EntityQualityConfig).filter(
                EntityQualityConfig.config_key == 'ml_training_min_samples'
            ).first()
            min_samples = int(config.config_value) if config else 100

            if len(X) < min_samples:
                logger.warning(f"Insufficient training data for {language}: {len(X)} < {min_samples}")
                return None

            # Check class balance
            valid_count = sum(y)
            invalid_count = len(y) - valid_count
            if valid_count < 10 or invalid_count < 10:
                logger.warning(f"Imbalanced training data for {language}: valid={valid_count}, invalid={invalid_count}")
                return None

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            # Train model
            if model_type == 'logistic':
                model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
            elif model_type == 'random_forest':
                model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
            else:
                logger.error(f"Unknown model type: {model_type}")
                return None

            logger.info(f"Training {model_type} model for {language} with {len(X_train)} samples")
            model.fit(X_train, y_train)

            # Evaluate model
            y_pred = model.predict(X_test)
            metrics = {
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'precision': float(precision_score(y_test, y_pred, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, zero_division=0)),
                'f1': float(f1_score(y_test, y_pred, zero_division=0)),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }

            logger.info(f"Model metrics for {language}: accuracy={metrics['accuracy']:.3f}, f1={metrics['f1']:.3f}")

            # Save model
            model_version = f"v1.{int(datetime.utcnow().timestamp())}"
            self._save_model(model, language, model_version, model_type, metrics, len(X))

            # Extract and save feature importance
            self._save_feature_importance(model, language, model_version)

            logger.info(f"Successfully trained model {model_version} for {language}")
            return model_version

        except Exception as e:
            logger.error(f"Failed to train model for {language}: {e}", exc_info=True)
            return None

    def _save_model(
        self,
        model,
        language: str,
        model_version: str,
        model_type: str,
        metrics: Dict[str, float],
        training_samples: int
    ):
        """Save trained model to database"""
        try:
            from app.database.models import EntityQualityModel

            # Pickle model
            model_bytes = joblib.dumps(model)

            # Deactivate old models
            self.db.query(EntityQualityModel).filter(
                EntityQualityModel.language == language,
                EntityQualityModel.is_active == True
            ).update({'is_active': False})

            # Create new model entry
            new_model = EntityQualityModel(
                model_version=model_version,
                language=language,
                model_type=model_type,
                model_data=model_bytes,
                performance_metrics=metrics,
                training_samples_count=training_samples,
                is_active=True
            )

            self.db.add(new_model)
            self.db.commit()

            # Update supported_languages ml_model_available flag
            from app.database.models import SupportedLanguage
            self.db.query(SupportedLanguage).filter(
                SupportedLanguage.language_code == language
            ).update({'ml_model_available': True})
            self.db.commit()

            logger.info(f"Saved model {model_version} for {language} to database")

        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            self.db.rollback()
            raise

    def _save_feature_importance(self, model, language: str, model_version: str):
        """Extract and save feature importance"""
        try:
            from app.database.models import EntityQualityFeature

            feature_names = [
                'length', 'word_count', 'vowel_ratio', 'consonant_ratio',
                'digit_ratio', 'special_char_ratio', 'repetitive_char_score',
                'dict_valid_ratio', 'stop_word_ratio', 'has_field_label_suffix',
                'title_case', 'spacy_confidence',
                'is_person', 'is_organization', 'is_location'
            ]

            # Get feature importance
            if hasattr(model, 'feature_importances_'):
                # RandomForest
                importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                # LogisticRegression
                importances = np.abs(model.coef_[0])
            else:
                logger.warning("Model does not support feature importance")
                return

            # Normalize to 0-1
            if importances.max() > 0:
                importances = importances / importances.max()

            # Save to database
            for name, importance in zip(feature_names, importances):
                feature = EntityQualityFeature(
                    feature_name=name,
                    importance_score=float(importance),
                    language=language,
                    model_version=model_version
                )
                self.db.add(feature)

            self.db.commit()
            logger.info(f"Saved feature importance for {model_version}")

        except Exception as e:
            logger.error(f"Failed to save feature importance: {e}")
            self.db.rollback()

    def load_active_model(self, language: str):
        """
        Load active ML model for language

        Args:
            language: Language code

        Returns:
            Loaded sklearn model or None
        """
        try:
            from app.database.models import EntityQualityModel

            model_entry = self.db.query(EntityQualityModel).filter(
                EntityQualityModel.language == language,
                EntityQualityModel.is_active == True
            ).first()

            if not model_entry:
                logger.debug(f"No active model found for {language}")
                return None

            # Unpickle model
            model = joblib.loads(model_entry.model_data)
            logger.debug(f"Loaded model {model_entry.model_version} for {language}")
            return model

        except Exception as e:
            logger.error(f"Failed to load model for {language}: {e}")
            return None

    def predict_confidence(
        self,
        features: Dict[str, float],
        language: str
    ) -> Optional[float]:
        """
        Predict entity confidence using ML model

        Args:
            features: Feature dictionary
            language: Language code

        Returns:
            Confidence score between 0.0 and 1.0, or None if no model
        """
        try:
            model = self.load_active_model(language)
            if not model:
                return None

            # Convert features to vector
            feature_vector = self._dict_to_feature_vector(features)
            X = np.array([feature_vector])

            # Predict probability
            probabilities = model.predict_proba(X)
            confidence = float(probabilities[0][1])  # Probability of class 1 (valid)

            return confidence

        except Exception as e:
            logger.error(f"Failed to predict confidence: {e}")
            return None

    def add_feedback_to_training_data(
        self,
        entity_value: str,
        entity_type: str,
        language: str,
        is_valid: bool,
        features: Dict[str, float],
        source: str = 'user_feedback',
        user_id: Optional[str] = None,
        document_id: Optional[str] = None
    ):
        """
        Add entity feedback to training data

        Args:
            entity_value: Entity text
            entity_type: Entity type
            language: Language code
            is_valid: Whether entity is valid
            features: Extracted features
            source: Data source (user_blacklist, manual_label, auto_feedback)
            user_id: Optional user ID
            document_id: Optional document ID
        """
        try:
            from app.database.models import EntityQualityTrainingData

            training_entry = EntityQualityTrainingData(
                entity_value=entity_value,
                entity_type=entity_type,
                language=language,
                is_valid=is_valid,
                features=features,  # JSONB column
                source=source,
                user_id=user_id,
                document_id=document_id
            )

            self.db.add(training_entry)
            self.db.commit()

            logger.info(f"Added training data: {entity_value} ({language}) - valid={is_valid}, source={source}")

        except Exception as e:
            logger.error(f"Failed to add training data: {e}")
            self.db.rollback()

    def sync_blacklist_to_training_data(self, language: Optional[str] = None):
        """
        Sync entity_blacklist entries to training_data

        Args:
            language: Optional language filter, syncs all if None
        """
        try:
            from app.database.models import EntityBlacklist, EntityQualityTrainingData
            from app.services.entity_quality_service import EntityQualityService

            # Get blacklist entries not yet in training data
            query = self.db.query(EntityBlacklist)
            if language:
                query = query.filter(EntityBlacklist.language == language)

            blacklist_entries = query.all()

            quality_service = EntityQualityService(self.db)
            added_count = 0

            for entry in blacklist_entries:
                # Check if already in training data
                exists = self.db.query(EntityQualityTrainingData).filter(
                    EntityQualityTrainingData.entity_value == entry.entity_value,
                    EntityQualityTrainingData.language == entry.language,
                    EntityQualityTrainingData.source == 'user_blacklist'
                ).first()

                if not exists:
                    # Extract features
                    features = quality_service.extract_features(
                        text=entry.entity_value,
                        entity_type=entry.entity_type,
                        language=entry.language,
                        base_confidence=0.5
                    )

                    # Add to training data
                    self.add_feedback_to_training_data(
                        entity_value=entry.entity_value,
                        entity_type=entry.entity_type,
                        language=entry.language,
                        is_valid=False,  # Blacklist = invalid
                        features=features,
                        source='user_blacklist',
                        user_id=entry.user_id
                    )
                    added_count += 1

            logger.info(f"Synced {added_count} blacklist entries to training data for language={language or 'all'}")
            return added_count

        except Exception as e:
            logger.error(f"Failed to sync blacklist to training data: {e}")
            return 0

    def get_training_stats(self, language: Optional[str] = None) -> Dict:
        """
        Get training data statistics

        Args:
            language: Optional language filter

        Returns:
            Dictionary with statistics
        """
        try:
            from app.database.models import EntityQualityTrainingData
            from sqlalchemy import func

            query = self.db.query(
                EntityQualityTrainingData.language,
                EntityQualityTrainingData.is_valid,
                func.count(EntityQualityTrainingData.id).label('count')
            )

            if language:
                query = query.filter(EntityQualityTrainingData.language == language)

            query = query.group_by(
                EntityQualityTrainingData.language,
                EntityQualityTrainingData.is_valid
            )

            results = query.all()

            stats = {}
            for lang, is_valid, count in results:
                if lang not in stats:
                    stats[lang] = {'valid': 0, 'invalid': 0, 'total': 0}

                if is_valid:
                    stats[lang]['valid'] = count
                else:
                    stats[lang]['invalid'] = count

                stats[lang]['total'] += count

            return stats

        except Exception as e:
            logger.error(f"Failed to get training stats: {e}")
            return {}


def get_entity_ml_service(db: Session) -> EntityMLService:
    """Factory function to create EntityMLService with database session"""
    return EntityMLService(db)
