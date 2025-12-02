# ML-Based Entity Quality Scoring System - Implementation Plan

## Status: IN PROGRESS
**Started:** 2025-12-01
**Current Session:** Implementing industry-standard ML solution with learnable confidences

---

## Problem Statement
Current entity extraction returns garbage (OCR errors, field labels, incomplete addresses):
- "Frankfurt am Main Tel" - field label concatenated
- "HHEHERRHEREROL" - OCR garbage
- "64283 Darmstadt www" - technical term concatenated
- "Beleg-Nr" - field labels extracted as entities
- ALL entities show `confidence: 1.0` (hardcoded, not calculated)

**Root Causes:**
1. Hardcoded confidence (0.85) instead of using spaCy's real scores
2. Hardcoded weights (0.3, 0.6, 1.2) - not learnable
3. Hardcoded languages (de, en, fr, ru) - not dynamic
4. Binary dictionary validation (pass/fail) - not nuanced
5. No machine learning - system can't improve from user feedback

---

## Solution: Industry-Standard ML Architecture

### Key Principles
1. **Database-Driven Configuration** - All weights/thresholds in DB, not code
2. **Dynamic Language Support** - Languages from DB with hunspell/spacy config
3. **Machine Learning** - Sklearn models trained on user feedback
4. **Feature Engineering** - Extract 12+ numeric features from entities
5. **Active Learning** - System improves as users correct mistakes
6. **ML-Learned Thresholds** - sklearn learns optimal thresholds automatically (NO hardcoded logic)

### Threshold Management Strategy
**Primary Approach (ML-based):**
- sklearn models (LogisticRegression/RandomForest) automatically learn optimal thresholds
- Features are raw numeric values (vowel_ratio, length, etc.)
- Model training determines which thresholds separate good/bad entities
- NO manual threshold tuning needed
- Improves automatically from user feedback

**Fallback Approach (Rule-based, when no ML model yet):**
- All thresholds stored in `entity_quality_config` table
- Examples: `threshold_length_very_short=2.0`, `threshold_vowel_ratio_low=0.15`
- Admin can tune via database without code changes
- Used only until ML model is trained for that language

---

## Database Schema (Migration 032)

### 1. `entity_quality_config`
**Purpose:** Store ALL configurable weights and thresholds
```sql
- config_key: length_very_short_penalty, pattern_repetitive_severe, etc.
- config_value: 0.1, 0.3, 1.2, etc.
- category: length, pattern, dictionary, ml_weight, ml_threshold
- min_value, max_value: Valid ranges for A/B testing
```

**Examples:**
- `length_very_short_penalty = 0.1` (entities < 2 chars)
- `dict_all_valid_bonus = 1.2` (100% words valid)
- `ml_confidence_threshold = 0.75` (min confidence to keep entity)

### 2. `entity_quality_training_data`
**Purpose:** Store labeled examples for ML training
```sql
- entity_value, entity_type, language, is_valid
- confidence_score, features (JSONB)
- source: user_blacklist, manual_label, auto_feedback
- user_id, document_id (for tracking)
```

**Data Sources:**
- User blacklists (negative examples)
- Approved entities (positive examples)
- Manual labeling interface (future)

### 3. `entity_quality_models`
**Purpose:** Store trained sklearn models (pickled)
```sql
- model_version: v1.0.0, v1.1.0, etc.
- language: de, en, fr, ru
- model_type: LogisticRegression, RandomForest
- model_data: BYTEA (pickled sklearn model)
- performance_metrics: {accuracy: 0.94, f1: 0.91, ...}
- is_active: true/false
```

### 4. `supported_languages`
**Purpose:** Dynamic language configuration (REPLACES hardcoded dict)
```sql
- language_code: de, en, fr, ru
- hunspell_dict: de_DE, en_US, fr_FR, ru_RU
- spacy_model: de_core_news_md, en_core_web_md, ...
- ml_model_available: true/false
- stop_words_count, field_labels_count
```

### 5. `entity_quality_features`
**Purpose:** Track feature importance from trained models
```sql
- feature_name: length, vowel_ratio, dict_valid_ratio, ...
- importance_score: 0.0 to 1.0
- language: de, en, fr, ru
```

---

## Feature Engineering (12+ Features)

### Features Extracted from Each Entity:
1. **length** - Character count
2. **word_count** - Number of words
3. **vowel_ratio** - Vowels / total letters
4. **consonant_ratio** - Consonants / total letters
5. **digit_ratio** - Digits / total chars
6. **special_char_ratio** - Special chars / total chars
7. **repetitive_char_score** - Penalty for "AAA", "BBB", etc.
8. **dict_valid_ratio** - % of words valid in Hunspell
9. **stop_word_ratio** - % of words that are stop words
10. **has_field_label_suffix** - Boolean (Tel, Fax, www, Nr detected)
11. **title_case** - Boolean (proper capitalization)
12. **spacy_confidence** - spaCy's native confidence score
13. **entity_type_encoded** - One-hot encoding of PERSON/ORG/LOCATION

---

## ML Pipeline

### Training Flow:
```
1. Collect training data from:
   - entity_blacklist (negative examples)
   - Approved extractions (positive examples)
   - Manual labels (future)

2. Extract features for each example

3. Train sklearn model:
   - LogisticRegression (fast, interpretable)
   - OR RandomForest (better accuracy)
   - OR XGBoost (production-grade)

4. Evaluate on test set:
   - Accuracy, Precision, Recall, F1
   - Store metrics in entity_quality_models.performance_metrics

5. Save model:
   - Pickle sklearn model
   - Store in entity_quality_models.model_data
   - Mark as active

6. Extract feature importance:
   - Save to entity_quality_features table
```

### Prediction Flow:
```
1. Entity extracted by spaCy

2. Extract features (12+ numeric values)

3. Load active ML model for language

4. If model exists:
   - Predict: model.predict_proba(features)
   - Use predicted confidence

   If no model yet:
   - Use rule-based scoring (current approach)
   - With DB-driven weights (NOT hardcoded)

5. Apply final threshold (from entity_quality_config)

6. Return confidence score
```

### Feedback Loop:
```
1. User reports bad entity → entity_blacklist

2. Trigger: Add to entity_quality_training_data
   - entity_value, entity_type, language
   - is_valid = false
   - source = 'user_blacklist'
   - features = extracted features

3. When training_data reaches threshold (e.g., 100 samples):
   - Auto-trigger retraining
   - OR admin clicks "Retrain Model" button

4. New model deployed → better confidence scores

5. System improves over time (Active Learning)
```

---

## Code Architecture

### 1. `entity_quality_service.py` (REWRITE)
**Changes:**
- Load config from `entity_quality_config` (NOT hardcoded)
- Load languages from `supported_languages` (NOT hardcoded)
- Implement `extract_features(entity) → Dict[str, float]`
- Use ML model if available, else rule-based
- All weights from DB

### 2. `entity_ml_service.py` (NEW)
**Functions:**
- `collect_training_data(language) → X, y`
- `train_model(X, y, model_type='logistic') → sklearn model`
- `evaluate_model(model, X_test, y_test) → metrics`
- `save_model(model, language, version) → DB`
- `load_active_model(language) → sklearn model`
- `predict_confidence(features, language) → float`
- `add_feedback_to_training_data(entity, is_valid, source)`

### 3. `entity_extraction_service.py` (UPDATE)
**Changes:**
- Extract spaCy's REAL confidence: `ent._.score` or similar
- Pass to quality_service: `base_confidence=spacy_confidence` (NOT 0.85)
- Pass db session: `calculate_confidence(..., db=db)`

### 4. API Endpoints ✅ IMPLEMENTED
**File:** `backend/app/api/entity_quality.py`

**POST /api/v1/entity-quality/retrain**
- Trigger model retraining for specific language or all languages
- Request body:
  ```json
  {
    "language": "de",  // optional, null = all languages
    "model_type": "logistic",  // or "random_forest"
    "sync_blacklist": true
  }
  ```
- Returns:
  ```json
  {
    "success": true,
    "message": "Successfully trained models for 2 languages",
    "models_trained": {
      "de": "v1.1733097600",
      "en": "v1.1733097601"
    },
    "training_stats": {
      "de": {"valid": 80, "invalid": 70, "total": 150},
      "en": {"valid": 45, "invalid": 38, "total": 83}
    }
  }
  ```
- Requires: Admin privileges

**POST /api/v1/entity-quality/sync-blacklist**
- Sync entity_blacklist entries to training data
- Request body:
  ```json
  {
    "language": "de"  // optional, null = all languages
  }
  ```
- Returns:
  ```json
  {
    "success": true,
    "message": "Synced 15 blacklist entries to training data",
    "synced_count": 15
  }
  ```
- Requires: Admin privileges

**GET /api/v1/entity-quality/stats**
- Get training data statistics
- Returns:
  ```json
  {
    "stats": {
      "de": {"valid": 80, "invalid": 70, "total": 150},
      "en": {"valid": 45, "invalid": 38, "total": 83}
    }
  }
  ```
- Requires: Admin privileges

**GET /api/v1/entity-quality/models**
- List all trained models with performance metrics
- Returns:
  ```json
  {
    "models": [
      {
        "model_version": "v1.1733097600",
        "language": "de",
        "model_type": "LogisticRegression",
        "is_active": true,
        "training_samples_count": 150,
        "performance_metrics": {
          "accuracy": 0.917,
          "precision": 0.905,
          "recall": 0.928,
          "f1": 0.916
        },
        "created_at": "2024-12-02T10:30:00Z"
      }
    ]
  }
  ```
- Requires: Admin privileges

---

## Existing Database Tables (REUSE)

✅ **stop_words** - 129 EN, 204 DE, 184 FR, 211 RU
   Columns: `word`, `language_code`, `is_active`

✅ **entity_field_labels** - Field labels for filtering
   Columns: `language`, `label_text`, `description`

✅ **entity_blacklist** - User-reported bad entities
   Columns: `language`, `entity_value`, `entity_type`, `user_id`

---

## Implementation Status

### Phase 1: Database Setup ✅ COMPLETE
- ✅ Created migration 032 with 6 tables (added entity_type_patterns)
- ✅ Populated entity_quality_config with 41 default weights/thresholds
- ✅ Populated supported_languages with de/en/fr/ru
- ✅ Populated entity_type_patterns with 45 org suffixes for all languages
- ✅ Created database models in models.py

### Phase 2: Feature Extraction ✅ COMPLETE
- ✅ Rewrote entity_quality_service.py (ZERO hardcoded values)
- ✅ Loads config from entity_quality_config table
- ✅ Loads languages from supported_languages table
- ✅ Loads stop_words, field_labels, type_patterns from database
- ✅ Implemented `extract_features()` - 15 features
- ✅ Database-driven thresholds for all scoring logic

### Phase 3: ML Training ✅ COMPLETE
- ✅ Created entity_ml_service.py with sklearn integration
- ✅ Implemented training pipeline (LogisticRegression/RandomForest)
- ✅ Implemented model save/load (pickle to BYTEA)
- ✅ Implemented feature importance tracking
- ✅ Added training data collection from blacklist
- ✅ Added training statistics reporting

### Phase 4: ML Prediction ✅ COMPLETE
- ✅ Implemented `predict_confidence()` using trained model
- ✅ Falls back to rule-based if no model available
- ✅ Updated entity_extraction_service.py to use spaCy's real confidence
- ✅ Passes db session to quality service

### Phase 5: Feedback Loop ✅ COMPLETE
- ✅ Implemented sync blacklist → training_data
- ✅ Created retrain API endpoints (POST /api/v1/entity-quality/retrain)
- ✅ Created sync API endpoint (POST /api/v1/entity-quality/sync-blacklist)
- ✅ Created stats API endpoint (GET /api/v1/entity-quality/stats)
- ✅ Created models list API endpoint (GET /api/v1/entity-quality/models)

### Phase 6: Testing & Deployment ⏳ PENDING
- ⏳ Run migration 032: `alembic upgrade head`
- ⏳ Restart backend and verify router loaded
- ⏳ Test with parking receipt document
- ⏳ Verify garbage entities filtered
- ⏳ Train initial ML models
- ⏳ Monitor confidence scores in production

---

## Expected Results

### Before (Current):
```
"HHEHERRHEREROL" → confidence: 1.0 → NOT filtered
"Frankfurt am Main Tel" → confidence: 1.0 → NOT filtered
"Beleg-Nr" → confidence: 1.0 → NOT filtered
```

### After (ML System):
```
"HHEHERRHEREROL" → confidence: 0.12 → FILTERED (< 0.75)
"Frankfurt am Main Tel" → confidence: 0.45 → FILTERED
"Beleg-Nr" → confidence: 0.30 → FILTERED
"Frankfurt am Main" → confidence: 0.96 → KEPT
"Parkhaus-Betriebs GmbH" → confidence: 0.94 → KEPT
```

### Learning Over Time:
```
Week 1: 85% accuracy (rule-based + initial training data)
Week 2: 89% accuracy (100 user corrections → retrain)
Week 4: 93% accuracy (300 corrections → retrain)
Week 8: 96% accuracy (stable, production-ready)
```

---

## Dependencies

**Python Packages:**
- `scikit-learn` - ML models (LogisticRegression, RandomForest)
- `joblib` - Model serialization
- `numpy` - Feature arrays
- `pandas` - Data manipulation (optional)

**Add to requirements.txt:**
```
scikit-learn>=1.3.0
joblib>=1.3.0
```

---

## Configuration Management

### A/B Testing Weights:
```sql
-- Test different thresholds
UPDATE entity_quality_config
SET config_value = 0.70
WHERE config_key = 'ml_confidence_threshold';

-- Monitor impact on filter rate
-- Roll back if too aggressive
```

### Model Versioning:
```sql
-- Deploy new model
UPDATE entity_quality_models
SET is_active = true
WHERE model_version = 'v1.2.0' AND language = 'de';

-- Deactivate old model
UPDATE entity_quality_models
SET is_active = false
WHERE model_version = 'v1.1.0' AND language = 'de';
```

---

## Monitoring & Metrics

### Track in Production:
1. **Entity Filter Rate** - % entities filtered vs kept
2. **Blacklist Growth** - New blacklist entries per week
3. **Model Accuracy** - Precision/Recall on test set
4. **Feature Importance** - Which features matter most
5. **Confidence Distribution** - Histogram of scores

### Alerts:
- Filter rate > 80% → Too aggressive
- Filter rate < 10% → Too lenient
- Blacklist spike → Quality degradation
- Model accuracy < 85% → Retrain needed

---

## Future Enhancements

1. **Deep Learning** - Use transformer models (BERT) for semantic understanding
2. **Entity Linking** - Link to knowledge bases (Wikipedia, GeoNames)
3. **Context Features** - Use surrounding text for validation
4. **Multi-task Learning** - Joint training with NER model
5. **Online Learning** - Real-time model updates
6. **Explainability** - SHAP values to explain confidence scores

---

---

## Deployment Instructions

### Step 1: Install Dependencies
```bash
cd backend
pip install scikit-learn>=1.3.0 joblib>=1.3.0
```

### Step 2: Run Migration
```bash
# Check current version
alembic current

# Run migration 032
alembic upgrade head

# Verify tables created
alembic current  # Should show: 032_ml_entity_quality (head)
```

**Expected output:**
- ✅ 6 tables created
- ✅ 41 config rows inserted
- ✅ 4 language rows inserted (de, en, fr, ru)
- ✅ 45 entity pattern rows inserted

### Step 3: Restart Backend
```bash
# Stop backend (Ctrl+C)
# Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Verify in logs:**
```
✓ EntityQuality router loaded
[ENTITY QUALITY] Loaded 41 ML configuration parameters from database
[ENTITY QUALITY] Loaded 4 supported languages
```

### Step 4: Initial Testing (Rule-Based Mode)
Upload test invoices and check entity extraction.

**Expected:** Garbage entities filtered based on DB thresholds.

### Step 5: Train ML Models (Optional)
```bash
# Using API (requires admin token)
curl -X POST http://localhost:8000/api/v1/entity-quality/sync-blacklist \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"language": null}'

curl -X POST http://localhost:8000/api/v1/entity-quality/retrain \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_type": "logistic", "sync_blacklist": true}'
```

**Or using Python:**
```python
from app.database.connection import db_manager
from app.services.entity_ml_service import get_entity_ml_service

db = db_manager.session_local()
ml_service = get_entity_ml_service(db)

# Sync blacklist
count = ml_service.sync_blacklist_to_training_data()
print(f"Synced {count} entries")

# Check stats
stats = ml_service.get_training_stats()
print(stats)

# Train model (needs 100+ samples)
if stats.get('de', {}).get('total', 0) >= 100:
    version = ml_service.train_model('de', 'logistic')
    print(f"Trained model: {version}")

db.close()
```

---

## Files Modified/Created

### Created Files:
1. `backend/alembic/versions/032_add_ml_entity_quality_system.py` - Migration
2. `backend/app/services/entity_ml_service.py` - ML training/prediction
3. `backend/app/api/entity_quality.py` - API endpoints
4. `ML_ENTITY_QUALITY_PLAN.md` - This documentation

### Modified Files:
1. `backend/app/database/models.py` - Added 6 models
2. `backend/app/services/entity_quality_service.py` - Complete rewrite (NO hardcoded values)
3. `backend/app/services/entity_extraction_service.py` - Use real spaCy confidence, pass db
4. `backend/app/main.py` - Registered EntityQuality router
5. `backend/requirements.txt` - Added sklearn, joblib

---

## Notes for Session Reset

If session resets, continue from:
1. Check last completed todo item
2. Read this plan document
3. Check database: `alembic current`
4. Check code: Files listed above
5. Continue with Phase 6: Testing & Deployment

**Key Context:**
- ✅ Implementation COMPLETE - ready for testing
- User wants industry-standard ML solution
- NO hardcoded values (weights, languages, thresholds)
- Learnable confidences from user feedback
- Database-driven configuration
- Clean, smart, dynamic architecture
- Complementary to existing category classification ML system
