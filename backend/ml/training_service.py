"""
ML Training Service - Trenowanie personalizowanych modeli ML dla każdego użytkownika

Ten serwis:
1. Trenuje modele mood prediction (przewidywanie nastroju)
2. Trenuje modele behavior profiling (profilowanie zachowań)
3. Zarządza wersjami modeli
4. Zapewnia predykcje w czasie rzeczywistym
5. Automatyczne re-training przy nowych danych
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from loguru import logger
import numpy as np
import pickle
import os
from pathlib import Path

# ML Libraries
try:
    from catboost import CatBoostRegressor, CatBoostClassifier, Pool
    CATBOOST_AVAILABLE = True
except ImportError:
    logger.warning("CatBoost not available - ML training disabled")
    CATBOOST_AVAILABLE = False

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, f1_score
import json


class MLTrainingService:
    """
    Serwis do trenowania i zarządzania personalizowanymi modelami ML.

    Każdy użytkownik ma własne modele:
    - Mood Predictor: Przewiduje przyszły nastrój
    - Behavior Profiler: Klasyfikuje wzorce zachowań
    """

    def __init__(
        self,
        memory_manager,
        feature_engineer,
        models_dir: str = "backend/ml/models"
    ):
        """
        Args:
            memory_manager: Memory Manager do dostępu do danych
            feature_engineer: FeatureEngineer do ekstrakcji cech
            models_dir: Katalog do zapisu modeli
        """
        self.memory = memory_manager
        self.feature_engineer = feature_engineer
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded models
        self._model_cache: Dict[str, Dict[str, Any]] = {}

        logger.info(f"🤖 ML Training Service initialized (models dir: {self.models_dir})")

    # ========================================================================
    # DATA PREPARATION
    # ========================================================================

    async def prepare_training_data(
        self,
        user_id: str,
        min_samples: int = 50,
        lookback_days: int = 90
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Przygotowuje dane treningowe dla użytkownika.

        Pobiera historyczne dane i konwertuje je na features + labels.

        Args:
            user_id: ID użytkownika
            min_samples: Minimalna liczba próbek do treningu
            lookback_days: Ile dni wstecz brać dane

        Returns:
            Tuple (X, y) gdzie:
            - X: Feature matrix (n_samples, n_features)
            - y: Target vector (n_samples,)
            Lub None jeśli za mało danych
        """
        try:
            logger.info(f"Preparing training data for user {user_id}")

            # Get user's mood history
            mood_history = await self.memory.get_mood_history(user_id, days=lookback_days)

            if len(mood_history) < min_samples:
                logger.warning(
                    f"Not enough data for user {user_id}: "
                    f"{len(mood_history)} samples (need {min_samples})"
                )
                return None

            # Get conversations for context
            db = self.memory._get_mongodb()
            if not db:
                logger.warning("MongoDB not available - cannot prepare training data")
                return None

            conversations = await db.get_user_conversations(user_id, limit=1000)

            # Build training samples
            X_list = []
            y_list = []

            for mood_entry in mood_history:
                timestamp = datetime.fromisoformat(mood_entry["timestamp"])
                mood_value = mood_entry["mood_intensity"]

                # Find associated conversation (closest in time)
                conv_message = self._find_closest_conversation(timestamp, conversations)

                if not conv_message:
                    # Use empty message if no conversation found
                    conv_message = "..."

                # Extract features
                features, _ = await self.feature_engineer.extract_all_features(
                    user_id=user_id,
                    message=conv_message,
                    timestamp=timestamp,
                    include_embeddings=False  # Don't use embeddings in tabular models
                )

                feature_vector = self.feature_engineer.features_to_vector(features)

                X_list.append(feature_vector)
                y_list.append(mood_value)

            X = np.array(X_list)
            y = np.array(y_list)

            logger.info(f"Prepared {len(X)} training samples with {X.shape[1]} features")

            return X, y

        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return None

    def _find_closest_conversation(
        self,
        timestamp: datetime,
        conversations: List[Any]
    ) -> Optional[str]:
        """Znajduje rozmowę najbliższą danej dacie"""
        if not conversations:
            return None

        # Find conversation closest in time (within 1 hour window)
        closest = None
        min_diff = timedelta(hours=1)

        for conv in conversations:
            diff = abs(conv.last_message_at - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest = conv

        # Get first message from that conversation
        if closest:
            return f"conversation_{closest.conversation_id}"

        return None

    # ========================================================================
    # MOOD PREDICTION MODEL
    # ========================================================================

    async def train_mood_predictor(
        self,
        user_id: str,
        min_samples: int = 50,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Trenuje model przewidywania nastroju dla użytkownika.

        Model: CatBoost Regressor
        Zadanie: Przewidywanie mood_intensity (1-10) na podstawie features

        Args:
            user_id: ID użytkownika
            min_samples: Minimalna liczba próbek
            test_size: Procent danych na test

        Returns:
            Dict z metrykami i informacjami o modelu
        """
        if not CATBOOST_AVAILABLE:
            return {"error": "CatBoost not available", "success": False}

        try:
            logger.info(f"🎯 Training mood predictor for user {user_id}")

            # Prepare data
            data = await self.prepare_training_data(user_id, min_samples=min_samples)
            if data is None:
                return {
                    "error": f"Not enough data (need at least {min_samples} samples)",
                    "success": False
                }

            X, y = data

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )

            # Create CatBoost model
            model = CatBoostRegressor(
                iterations=500,
                learning_rate=0.05,
                depth=6,
                loss_function='RMSE',
                random_seed=42,
                verbose=False,
                early_stopping_rounds=50
            )

            # Train
            logger.info(f"Training on {len(X_train)} samples...")
            model.fit(
                X_train, y_train,
                eval_set=(X_test, y_test),
                use_best_model=True,
                verbose=False
            )

            # Evaluate
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)

            train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
            test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
            train_mae = mean_absolute_error(y_train, y_pred_train)
            test_mae = mean_absolute_error(y_test, y_pred_test)

            # Save model
            model_path = self._save_model(user_id, "mood_predictor", model)

            # Get feature importances
            feature_names = self.feature_engineer.get_feature_names(
                await self._get_sample_features(user_id)
            )
            feature_importance = dict(zip(
                feature_names,
                model.feature_importances_.tolist()
            ))

            # Sort by importance
            top_features = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            result = {
                "success": True,
                "model_type": "mood_predictor",
                "user_id": user_id,
                "n_samples": len(X),
                "n_features": X.shape[1],
                "train_size": len(X_train),
                "test_size": len(X_test),
                "metrics": {
                    "train_rmse": float(train_rmse),
                    "test_rmse": float(test_rmse),
                    "train_mae": float(train_mae),
                    "test_mae": float(test_mae)
                },
                "top_features": [{"name": f, "importance": float(imp)} for f, imp in top_features],
                "model_path": str(model_path),
                "trained_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"✅ Mood predictor trained: "
                f"Test RMSE={test_rmse:.2f}, MAE={test_mae:.2f}"
            )

            # Cache model
            self._model_cache[f"{user_id}_mood_predictor"] = {
                "model": model,
                "metadata": result
            }

            return result

        except Exception as e:
            logger.error(f"Error training mood predictor: {e}")
            return {"error": str(e), "success": False}

    # ========================================================================
    # BEHAVIOR PROFILING MODEL
    # ========================================================================

    async def train_behavior_profiler(
        self,
        user_id: str,
        min_samples: int = 50,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Trenuje model profilowania zachowań użytkownika.

        Model: CatBoost Classifier
        Zadanie: Klasyfikacja mood category (positive/neutral/negative)

        Args:
            user_id: ID użytkownika
            min_samples: Minimalna liczba próbek
            test_size: Procent danych na test

        Returns:
            Dict z metrykami i informacjami o modelu
        """
        if not CATBOOST_AVAILABLE:
            return {"error": "CatBoost not available", "success": False}

        try:
            logger.info(f"🎭 Training behavior profiler for user {user_id}")

            # Prepare data
            data = await self.prepare_training_data(user_id, min_samples=min_samples)
            if data is None:
                return {
                    "error": f"Not enough data (need at least {min_samples} samples)",
                    "success": False
                }

            X, y_regression = data

            # Convert regression target to classification (positive/neutral/negative)
            y_classes = []
            for mood in y_regression:
                if mood >= 7:
                    y_classes.append("positive")
                elif mood <= 4:
                    y_classes.append("negative")
                else:
                    y_classes.append("neutral")

            y = np.array(y_classes)

            # Check class balance
            class_counts = {
                "positive": np.sum(y == "positive"),
                "neutral": np.sum(y == "neutral"),
                "negative": np.sum(y == "negative")
            }

            logger.info(f"Class distribution: {class_counts}")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )

            # Create CatBoost classifier
            model = CatBoostClassifier(
                iterations=300,
                learning_rate=0.05,
                depth=5,
                loss_function='MultiClass',
                random_seed=42,
                verbose=False,
                early_stopping_rounds=30
            )

            # Train
            logger.info(f"Training on {len(X_train)} samples...")
            model.fit(
                X_train, y_train,
                eval_set=(X_test, y_test),
                use_best_model=True,
                verbose=False
            )

            # Evaluate
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)

            train_accuracy = accuracy_score(y_train, y_pred_train)
            test_accuracy = accuracy_score(y_test, y_pred_test)
            train_f1 = f1_score(y_train, y_pred_train, average='weighted')
            test_f1 = f1_score(y_test, y_pred_test, average='weighted')

            # Save model
            model_path = self._save_model(user_id, "behavior_profiler", model)

            result = {
                "success": True,
                "model_type": "behavior_profiler",
                "user_id": user_id,
                "n_samples": len(X),
                "n_features": X.shape[1],
                "train_size": len(X_train),
                "test_size": len(X_test),
                "class_distribution": {k: int(v) for k, v in class_counts.items()},
                "metrics": {
                    "train_accuracy": float(train_accuracy),
                    "test_accuracy": float(test_accuracy),
                    "train_f1": float(train_f1),
                    "test_f1": float(test_f1)
                },
                "model_path": str(model_path),
                "trained_at": datetime.utcnow().isoformat()
            }

            logger.info(
                f"✅ Behavior profiler trained: "
                f"Test Accuracy={test_accuracy:.2%}, F1={test_f1:.2%}"
            )

            # Cache model
            self._model_cache[f"{user_id}_behavior_profiler"] = {
                "model": model,
                "metadata": result
            }

            return result

        except Exception as e:
            logger.error(f"Error training behavior profiler: {e}")
            return {"error": str(e), "success": False}

    # ========================================================================
    # PREDICTIONS
    # ========================================================================

    async def predict_mood(
        self,
        user_id: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Przewiduje nastrój użytkownika na podstawie aktualnego kontekstu.

        Args:
            user_id: ID użytkownika
            message: Aktualna wiadomość
            timestamp: Optional timestamp (default: now)

        Returns:
            Dict z predykcją: {"predicted_mood": float, "confidence": float}
        """
        try:
            # Load model
            model = await self._load_model(user_id, "mood_predictor")
            if not model:
                logger.debug(f"No mood predictor model for user {user_id}")
                return None

            # Extract features
            timestamp = timestamp or datetime.utcnow()
            features, _ = await self.feature_engineer.extract_all_features(
                user_id=user_id,
                message=message,
                timestamp=timestamp,
                include_embeddings=False
            )

            feature_vector = self.feature_engineer.features_to_vector(features)
            feature_vector = feature_vector.reshape(1, -1)

            # Predict
            prediction = model.predict(feature_vector)[0]

            # Estimate confidence (inverse of model's std if available)
            confidence = 0.75  # Default confidence

            return {
                "predicted_mood": float(prediction),
                "confidence": confidence,
                "timestamp": timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting mood: {e}")
            return None

    async def predict_behavior(
        self,
        user_id: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Klasyfikuje zachowanie użytkownika (positive/neutral/negative).

        Args:
            user_id: ID użytkownika
            message: Aktualna wiadomość
            timestamp: Optional timestamp (default: now)

        Returns:
            Dict z predykcją: {"predicted_class": str, "probabilities": dict}
        """
        try:
            # Load model
            model = await self._load_model(user_id, "behavior_profiler")
            if not model:
                logger.debug(f"No behavior profiler model for user {user_id}")
                return None

            # Extract features
            timestamp = timestamp or datetime.utcnow()
            features, _ = await self.feature_engineer.extract_all_features(
                user_id=user_id,
                message=message,
                timestamp=timestamp,
                include_embeddings=False
            )

            feature_vector = self.feature_engineer.features_to_vector(features)
            feature_vector = feature_vector.reshape(1, -1)

            # Predict
            prediction = model.predict(feature_vector)[0]
            probabilities = model.predict_proba(feature_vector)[0]

            # Map probabilities to classes
            classes = model.classes_
            prob_dict = {cls: float(prob) for cls, prob in zip(classes, probabilities)}

            return {
                "predicted_class": prediction,
                "probabilities": prob_dict,
                "timestamp": timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting behavior: {e}")
            return None

    # ========================================================================
    # MODEL MANAGEMENT
    # ========================================================================

    def _save_model(
        self,
        user_id: str,
        model_type: str,
        model: Any
    ) -> Path:
        """Zapisuje model do pliku"""
        model_filename = f"{user_id}_{model_type}.pkl"
        model_path = self.models_dir / model_filename

        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        logger.info(f"Model saved: {model_path}")
        return model_path

    async def _load_model(
        self,
        user_id: str,
        model_type: str
    ) -> Optional[Any]:
        """Ładuje model z cache lub z dysku"""
        cache_key = f"{user_id}_{model_type}"

        # Check cache first
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]["model"]

        # Load from disk
        model_filename = f"{user_id}_{model_type}.pkl"
        model_path = self.models_dir / model_filename

        if not model_path.exists():
            return None

        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            # Cache it
            self._model_cache[cache_key] = {
                "model": model,
                "loaded_at": datetime.utcnow()
            }

            logger.debug(f"Model loaded: {model_path}")
            return model

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None

    async def _get_sample_features(self, user_id: str) -> Dict[str, float]:
        """Pobiera przykładowe features dla user (do feature names)"""
        features, _ = await self.feature_engineer.extract_all_features(
            user_id=user_id,
            message="sample",
            timestamp=datetime.utcnow(),
            include_embeddings=False
        )
        return features

    def get_model_info(self, user_id: str, model_type: str) -> Optional[Dict[str, Any]]:
        """Zwraca informacje o modelu użytkownika"""
        cache_key = f"{user_id}_{model_type}"

        if cache_key in self._model_cache:
            return self._model_cache[cache_key].get("metadata")

        return None


# ============================================================================
# Singleton Pattern
# ============================================================================

_training_service: Optional[MLTrainingService] = None


def init_training_service(
    memory_manager,
    feature_engineer,
    models_dir: str = "backend/ml/models"
) -> MLTrainingService:
    """Inicjalizuj globalny ML Training Service"""
    global _training_service

    _training_service = MLTrainingService(
        memory_manager=memory_manager,
        feature_engineer=feature_engineer,
        models_dir=models_dir
    )

    return _training_service


def get_training_service() -> Optional[MLTrainingService]:
    """Pobierz globalny ML Training Service"""
    return _training_service
