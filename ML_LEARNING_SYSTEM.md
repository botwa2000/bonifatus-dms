# Bonifatus DMS - Machine Learning Keyword System

## Overview

The ML Keyword Learning System automatically improves document classification by learning from every user decision. It intelligently manages keyword weights across categories to minimize overlaps and maximize classification accuracy.

---

## Core Principle: Reinforcement Learning from User Feedback

Every time a user classifies a document (or confirms/corrects an AI suggestion), the system extracts a learning signal and adjusts keyword weights accordingly.

---

## Weight Adjustment Strategy

### 1. Base Weights by Category Role

```python
PRIMARY_CATEGORY_WEIGHT = +1.0
# The ONE category the user chose as PRIMARY
# This is the main category where the document belongs

SECONDARY_CATEGORY_WEIGHT = +0.3
# ALL other selected categories get EQUAL secondary weight
# These are "also relevant" but not primary
# No distinction between 2nd, 3rd, 4th, 5th category - all treated equally
```

**Key Principle**: Documents have ONE primary category and 0-4 secondary categories. All secondary categories are equally relevant (no ordering).

**Example:**
```
User selects:
- Primary: Insurance
- Also selected: Legal, Taxes

Learning weights:
"keyword" in Insurance: +1.0 (primary)
"keyword" in Legal: +0.3 (secondary)
"keyword" in Taxes: +0.3 (secondary - same as Legal!)
```

### 2. AI Prediction Feedback Weights

**Why does WRONG prediction get MORE points than CORRECT?**

```python
CORRECT_PREDICTION_BONUS = +0.2
WRONG_PREDICTION_BOOST = +0.5
```

#### The Reasoning:

**Correct Prediction (+0.2 - Small Reinforcement)**
- AI predicted "Banking", user confirmed "Banking"
- ✅ **This means the weights are already working correctly**
- The keyword already has sufficient weight in the Banking category
- We only need MINOR reinforcement to say "yes, keep doing this"
- Small bonus prevents over-fitting to patterns that already work

**Wrong Prediction (+0.5 - Aggressive Correction)**
- AI predicted "Legal" (80% confidence), user chose "Insurance"
- ❌ **This means there's a weight imbalance**
- Keywords likely have HIGHER weight in Legal than Insurance
- Example state:
  ```
  keyword "policy" in Legal: 3.0
  keyword "policy" in Insurance: 2.5  ← Too low!
  ```
- We need LARGER boost to flip this relationship:
  ```
  keyword "policy" in Legal: 3.0 (unchanged)
  keyword "policy" in Insurance: 2.5 + 1.0 + 0.5 = 4.0  ← Now dominant!
  ```
- Bigger boost ensures wrong predictions are corrected quickly

**Critical Insight**: When AI is wrong, it means the weight distribution is incorrect. We need aggressive correction to fix the imbalance. When AI is correct, weights are already good - just gentle reinforcement.

#### Example Scenario

**Document**: "Health Insurance Policy Renewal 2024"
**Keywords**: ["health", "insurance", "policy", "renewal"]
**AI Prediction**: Legal (confidence: 75%)
**User Choice**: Insurance (primary)

**Why did AI predict Legal?**
- "policy" has weight 3.5 in Legal (from many legal documents)
- "policy" has weight 2.0 in Insurance (insufficient)

**Learning adjustments:**
```python
# Wrong prediction boost for primary category
Insurance receives: +1.0 (primary) + 0.5 (wrong boost) = +1.5

# Legal receives: 0 (no penalty - it might still be relevant)

# New weights after learning:
"policy" in Insurance: 2.0 + 1.5 = 3.5
"policy" in Legal: 3.5 (unchanged)

# Next similar document:
AI will now see equal weights → other keywords will break the tie
If more insurance documents come, Insurance will pull ahead
```

**No Punishment for Wrong Category**: We never reduce weights. The AI might have been partially right (Legal could be a valid secondary category). We only boost the correct category to rise above it.

---

## 3. Confidence-Based Modifiers

The AI's confidence level modifies how much we learn:

```python
LOW_CONFIDENCE_CORRECT_MULTIPLIER = 1.5
# AI was uncertain (30%) but got it right
# Learn MORE because this was a hard case the system handled well

HIGH_CONFIDENCE_WRONG_MULTIPLIER = 1.3
# AI was very confident (90%) but WRONG
# Learn MORE to prevent this confident mistake from happening again
# This is the most dangerous case - overconfident wrong predictions
```

**Confidence Ranges:**
- Low: 0-50%
- Medium: 50-80%
- High: 80-100%

**Example:**
```python
# Scenario A: Low confidence, correct
AI predicts "Banking" (35% confidence), user confirms "Banking"
Boost = 0.2 × 1.5 = 0.3  # Learn more from this edge case

# Scenario B: High confidence, wrong
AI predicts "Legal" (92% confidence), user chooses "Insurance"
Boost = 0.5 × 1.3 = 0.65  # Aggressive correction needed
```

---

## 4. Handling Multi-Category Overlap (Critical Innovation)

### The Problem

Same keyword appears in multiple categories with similar weights → ambiguous classification

**Example:**
```
"invoice" in Taxes: 2.0
"invoice" in Invoices: 2.0
"invoice" in Legal: 2.0

→ AI cannot distinguish! Classification becomes random.
```

### The Solution: Differential Preservation

**Rule**: Maintain minimum weight differential of 0.3 between primary and other categories

```python
MINIMUM_WEIGHT_DIFFERENTIAL = 0.3
```

**Algorithm:**
1. User assigns document to categories: [Insurance (primary), Legal, Taxes]
2. For each keyword:
   - Calculate base boost for Insurance: +1.0 (primary)
   - Calculate base boost for Legal: +0.3 (secondary)
   - Calculate base boost for Taxes: +0.3 (secondary)
3. Check current weights:
   - "policy" in Insurance: 2.0 → would become 3.0
   - "policy" in Legal: 2.0 → would become 2.3
   - "policy" in Banking: 2.8 → unchanged
4. Check differential between primary and highest non-selected:
   - Insurance vs Banking: 3.0 - 2.8 = 0.2 ❌ (< 0.3, needs boost!)
5. Apply differential boost:
   - Add (0.3 - 0.2) = 0.1 to Insurance
   - Final: "policy" in Insurance: 3.1 ✓

**Result**: Primary category always has clear advantage (at least +0.3) over all other categories

---

## 5. Keyword Quality Filtering

Not all keywords are worth learning from:

### Exclusion Rules

```python
# 1. Stopwords (common words with no semantic value)
STOPWORDS = ["the", "and", "or", "but", "is", "are", "was", "were", ...]

# 2. Minimum length
MIN_KEYWORD_LENGTH = 3  # Skip "to", "in", "at"

# 3. Overly common (appears in too many categories)
MAX_CATEGORY_OVERLAP = 0.5  # Skip if appears in >50% of categories

# 4. Minimum document keywords
MIN_KEYWORDS_REQUIRED = 3  # Need at least 3 keywords to learn

# 5. Numeric-only keywords
SKIP_NUMERIC_ONLY = true  # Skip "2024", "123"
```

### Quality Score (Future Enhancement)

Each keyword gets a quality score before learning:

```python
quality_score = (
    specificity × 0.4 +      # How unique to this category?
    frequency × 0.3 +         # How often does it appear?
    length_score × 0.2 +      # Longer = more specific
    position_score × 0.1      # Earlier in document = more important
)

# Only learn from keywords with quality_score > 0.5
```

---

## 6. Weight Boundaries and Normalization

Prevent weights from growing unbounded or becoming too small:

```python
MIN_WEIGHT = 0.1  # Prevents keywords from disappearing
MAX_WEIGHT = 10.0  # Prevents one keyword from dominating

# Normalization function
def normalize_weight(weight: float) -> float:
    return max(MIN_WEIGHT, min(MAX_WEIGHT, weight))
```

**Decay Strategy** (future enhancement):
- Unused keywords slowly decay: weight × 0.99 every month
- Prevents ancient patterns from persisting forever
- Keeps system adaptive to changing document types

---

## 7. Complete Weight Calculation Formula

```python
def calculate_weight_adjustment(
    keyword: str,
    category_id: UUID,
    is_primary: bool,
    ai_predicted_category: Optional[UUID],
    ai_confidence: Optional[float]
) -> float:
    """
    Calculate how much to adjust keyword weight in a category

    Returns: weight adjustment (can be 0 if no adjustment needed)
    """

    # Base weight by category role
    if is_primary:
        adjustment = PRIMARY_CATEGORY_WEIGHT  # +1.0
    else:
        adjustment = SECONDARY_CATEGORY_WEIGHT  # +0.3

    # AI feedback bonus/boost (only for primary category)
    if is_primary and ai_predicted_category:
        if ai_predicted_category == category_id:
            # AI was correct - small reinforcement
            adjustment += CORRECT_PREDICTION_BONUS  # +0.2

            # Apply confidence modifier
            if ai_confidence and ai_confidence < 0.5:
                adjustment *= LOW_CONFIDENCE_CORRECT_MULTIPLIER  # ×1.5
        else:
            # AI was wrong - aggressive correction
            adjustment += WRONG_PREDICTION_BOOST  # +0.5

            # Apply confidence modifier
            if ai_confidence and ai_confidence > 0.8:
                adjustment *= HIGH_CONFIDENCE_WRONG_MULTIPLIER  # ×1.3

    return adjustment
```

**Example Calculations:**

```python
# Case 1: Primary category, AI correct, low confidence
adjustment = 1.0 + 0.2 = 1.2
adjustment *= 1.5 = 1.8

# Case 2: Primary category, AI wrong, high confidence
adjustment = 1.0 + 0.5 = 1.5
adjustment *= 1.3 = 1.95

# Case 3: Secondary category (no AI feedback bonuses)
adjustment = 0.3
```

---

## 8. Learning Event Logging

Every learning event is logged for analytics and debugging:

```sql
CREATE TABLE ml_learning_events (
    id UUID PRIMARY KEY,
    document_id UUID,
    user_id UUID,
    event_type VARCHAR(50),  -- 'upload', 'reclassification', 'confirmation'
    ai_predicted_category UUID,
    ai_confidence FLOAT,
    user_primary_category UUID,
    user_secondary_categories UUID[],
    keywords_learned JSONB,  -- {keyword: {category_id: weight_change}}
    learning_metadata JSONB,
    created_at TIMESTAMP
);
```

**Analytics queries:**
- Classification accuracy over time
- Most learned keywords per category
- Overlap reduction metrics
- User-specific learning patterns

---

## 9. Configuration System

All parameters are configurable via `system_settings` table:

```python
# Core toggles
ml_learning_enabled: true
ml_auto_learn_on_upload: true
ml_learn_from_reclassification: true

# Weight parameters
ml_primary_weight: 1.0
ml_secondary_weight: 0.3
ml_correct_prediction_bonus: 0.2
ml_wrong_prediction_boost: 0.5

# Confidence modifiers
ml_low_confidence_correct_multiplier: 1.5
ml_high_confidence_wrong_multiplier: 1.3

# Quality controls
ml_min_keywords_required: 3
ml_min_keyword_length: 3
ml_min_weight_differential: 0.3
ml_max_weight: 10.0
ml_min_weight: 0.1

# Advanced features
ml_learning_rate: 1.0  # Global multiplier for all learning
ml_specificity_scoring_enabled: false  # Future feature
ml_decay_enabled: false  # Future feature
ml_decay_rate: 0.99
```

---

## 10. Implementation Architecture

```
┌─────────────────────────────────────┐
│  User Uploads/Classifies Document  │
│  - Primary: Insurance               │
│  - Secondary: Legal, Taxes          │
└──────────────┬──────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  Extract Document Keywords           │
│  - Tokenize text                     │
│  - Remove stopwords                  │
│  - Apply quality filtering           │
│  Output: ["claim", "policy", ...]    │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  MLKeywordLearningService            │
│                                       │
│  learn_from_classification():        │
│    For each keyword:                 │
│      1. Load current weights          │
│      2. Calculate adjustment          │
│         - Primary: +1.0 + AI bonus    │
│         - Secondary: +0.3 (each)      │
│      3. Apply differential check      │
│      4. Update CategoryKeyword        │
│    Log learning event                 │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  Database Updates                     │
│  - CategoryKeyword.weight updated     │
│  - MLLearningEvent logged             │
│  - Classification cache cleared       │
└───────────────────────────────────────┘
```

---

## 11. Example Learning Scenarios

### Scenario A: First Time Learning

**Input:**
```
Document: "Car Insurance Claim 2024"
Keywords: ["car", "insurance", "claim"]
User chooses: Insurance (primary), Legal (secondary)
AI prediction: None (first document)
```

**Learning process:**
```python
For "car":
  - Insurance (primary): 0 + 1.0 = 1.0 (NEW)
  - Legal (secondary): 0 + 0.3 = 0.3 (NEW)

For "insurance":
  - Insurance (primary): 0 + 1.0 = 1.0 (NEW)
  - Legal (secondary): 0 + 0.3 = 0.3 (NEW)

For "claim":
  - Insurance (primary): 0 + 1.0 = 1.0 (NEW)
  - Legal (secondary): 0 + 0.3 = 0.3 (NEW)
```

**Result:**
```
All keywords now exist in both categories
Insurance has 3× stronger signal than Legal
Next similar document will likely predict Insurance
```

### Scenario B: Correct AI Prediction

**Input:**
```
Document: "Home Insurance Policy"
Keywords: ["home", "insurance", "policy"]
AI predicts: Insurance (78% confidence)
User confirms: Insurance (primary)
Current state:
  "insurance" in Insurance: 2.5
  "policy" in Insurance: 1.8
```

**Learning process:**
```python
# AI correct, medium-high confidence (no special multiplier)
adjustment = 1.0 (primary) + 0.2 (correct bonus) = 1.2

For "insurance":
  Insurance: 2.5 + 1.2 = 3.7

For "policy":
  Insurance: 1.8 + 1.2 = 3.0
```

**Result:**
```
Weights reinforced in Insurance category
Small boost prevents over-fitting
```

### Scenario C: Wrong AI Prediction

**Input:**
```
Document: "Medical Insurance Claim Form"
Keywords: ["medical", "insurance", "claim", "form"]
AI predicts: Medical (85% confidence) ← WRONG!
User chooses: Insurance (primary)
Current state:
  "claim" in Medical: 3.2
  "claim" in Insurance: 2.0  ← Too low!
```

**Learning process:**
```python
# AI wrong, high confidence
adjustment = 1.0 (primary) + 0.5 (wrong boost) = 1.5
adjustment *= 1.3 (high confidence wrong) = 1.95

For "claim":
  Insurance: 2.0 + 1.95 = 3.95 ✓ Now dominant!
  Medical: 3.2 (unchanged - no punishment)
```

**Result:**
```
"claim" now weighs more in Insurance (3.95) than Medical (3.2)
Next similar document will predict Insurance correctly
Aggressive boost fixed the imbalance
```

### Scenario D: Multi-Category with Overlap

**Input:**
```
Document: "Tax Invoice for Legal Services 2024"
Keywords: ["tax", "invoice", "legal", "services"]
User chooses: Taxes (primary), Legal (secondary)
Current state:
  "invoice" in Taxes: 2.0
  "invoice" in Legal: 1.9
  "invoice" in Invoices: 2.5  ← Problem: highest in non-selected category!
```

**Learning process:**
```python
# Step 1: Calculate base adjustments
Taxes (primary): 2.0 + 1.0 = 3.0
Legal (secondary): 1.9 + 0.3 = 2.2

# Step 2: Check differential with highest non-selected category
Taxes vs Invoices: 3.0 - 2.5 = 0.5 ✓ (> 0.3, OK)

# Step 3: Final weights
"invoice" in Taxes: 3.0
"invoice" in Legal: 2.2
"invoice" in Invoices: 2.5 (unchanged)
```

**Result:**
```
Clear winner: Taxes (3.0)
Legal secondary signal (2.2)
Invoices still high but not highest (2.5)
Next "tax invoice" document will predict Taxes
```

### Scenario E: Differential Boost Needed

**Input:**
```
Document: "Insurance Policy Document"
Keywords: ["insurance", "policy", "document"]
User chooses: Insurance (primary)
Current state:
  "policy" in Insurance: 2.0
  "policy" in Legal: 2.7  ← Higher than target category!
```

**Learning process:**
```python
# Step 1: Base adjustment
Insurance: 2.0 + 1.0 = 3.0

# Step 2: Check differential
Insurance vs Legal: 3.0 - 2.7 = 0.3 ✓ (exactly at threshold)

# If differential was < 0.3:
# Example: If Legal was 2.9
# Differential: 3.0 - 2.9 = 0.1 ❌
# Boost needed: 0.3 - 0.1 = 0.2
# Final: 3.0 + 0.2 = 3.2 ✓
```

---

## 12. Success Metrics

### Primary Metrics
- **Classification Accuracy**: % of documents where AI prediction matches user's primary choice
- **Learning Velocity**: How quickly accuracy improves with more data
- **Overlap Reduction**: % decrease in keywords with <0.3 differential

### Secondary Metrics
- **User Override Rate**: % of times user changes AI suggestion
- **Multi-Category Consistency**: Keywords maintain proper weight ratios
- **Keyword Coverage**: % of documents with sufficient learned keywords (>5)

### Target KPIs (After 1000 documents per user)
- Classification Accuracy: >85%
- High-confidence Accuracy: >95%
- User Override Rate: <20%
- Ambiguous Keywords: <10% of total

---

## 13. API Endpoints for Monitoring

### GET /api/v1/ml/learning-stats
```json
{
  "total_learning_events": 1234,
  "classification_accuracy": 87.5,
  "accuracy_trend": "+5.2% vs last month",
  "total_learned_keywords": 456,
  "high_confidence_accuracy": 94.3
}
```

### GET /api/v1/categories/keywords/overlaps
```json
{
  "overlaps": [
    {
      "keyword": "invoice",
      "categories": [
        {"id": "...", "name": "Taxes", "weight": 3.3},
        {"id": "...", "name": "Invoices", "weight": 2.3},
        {"id": "...", "name": "Legal", "weight": 2.0}
      ],
      "differential": 1.0,
      "severity": "low",  // low/medium/high
      "recommendation": "OK - clear winner exists"
    }
  ]
}
```

---

## 14. Current System Audit & Implementation Status

### ✅ Existing Infrastructure (Already in Database)

**Database Tables:**
1. **`system_settings`** - Configuration storage (active, in use)
   - Structure: `setting_key`, `setting_value`, `data_type`, `description`, `is_public`, `category`
   - Currently stores: file upload limits, keyword extraction params, OCR settings
   - **Ready for ML config:** Yes - just need to insert ML parameters

2. **`stop_words`** - Multilingual stopword filtering (exists, but EMPTY)
   - Structure: `word`, `language_code`, `is_active`, `created_at`
   - Currently populated: NONE
   - **Ready for use:** Yes - table exists, needs population

3. **`category_keywords`** - Keyword weights with learning tracking (active)
   - Structure: `category_id`, `keyword`, `language_code`, `weight`, `match_count`, `last_matched_at`, `is_system`
   - Currently populated: Initial weights for Insurance, Banking, Legal, Real Estate, Other, Invoices, Taxes
   - **Supports learning:** Yes - has weight field and match tracking

4. **`category_training_data`** - Classification decision logging (active)
   - Structure: `document_id`, `suggested_category_id`, `actual_category_id`, `was_correct`, `confidence`, `text_sample`, `language_code`, `user_id`
   - Currently used: Yes - logs every classification decision
   - **Analytics ready:** Yes - can query accuracy trends

**Existing Services:**
1. **`ml_learning_service.py`** - Basic learning implementation
   - Current capabilities:
     - Records classification decisions ✓
     - Adjusts weights for correct suggestions (multiplicative boost) ✓
     - Penalizes weights for wrong suggestions (multiplicative penalty) ✓
   - **Limitations:**
     - ❌ Only handles single category (not multi-category)
     - ❌ Uses multiplicative adjustments (not additive)
     - ❌ No confidence-based modifiers
     - ❌ No differential preservation
     - ❌ No stopword filtering
     - ❌ Loads config from old format (`classification_config` key)

**Backup Migrations (Not Applied):**
- `b0c1d2e3f4g5_populate_ml_initial_data.py` - Contains:
  - Stopwords for English, German, Russian (comprehensive lists)
  - Initial keyword weights for all categories
  - OCR spelling corrections
  - **Status:** In backup folder, not applied to active database

### ❌ What's Missing for Smart Learning

**In `system_settings` table (need to add):**
```python
ml_learning_enabled: true
ml_primary_weight: 1.0
ml_secondary_weight: 0.3
ml_correct_prediction_bonus: 0.2
ml_wrong_prediction_boost: 0.5
ml_low_confidence_correct_multiplier: 1.5
ml_high_confidence_wrong_multiplier: 1.3
ml_min_keywords_required: 3
ml_min_keyword_length: 3
ml_min_weight_differential: 0.3
ml_max_weight: 10.0
ml_min_weight: 0.1
ml_learning_rate: 1.0
```

**In `stop_words` table (need to populate):**
- English stopwords (~50 words)
- German stopwords (~50 words)
- Russian stopwords (~150 words)
- Framework for adding more languages

**In `ml_learning_service.py` (need to enhance):**
- Multi-category support (primary + secondary categories)
- Additive weight adjustments (current + boost, not current × factor)
- Confidence-based learning rate modifiers
- Differential preservation algorithm
- Load stopwords from database per language
- Quality filtering for keywords

### 📋 Implementation Strategy

**Step 1: Migration 015 - Populate ML Configuration**
Create `015_populate_ml_learning_config.py` to:
1. Insert ML learning parameters into `system_settings` table
2. Populate `stop_words` table from backup migration data
3. Keep language-agnostic design (easy to add French, Spanish, etc.)

**Step 2: Enhance `ml_learning_service.py`**
Replace/enhance existing methods:
1. **`learn_from_classification()`** - New signature with multi-category support
   ```python
   def learn_from_classification(
       document_id: UUID,
       document_keywords: List[str],
       primary_category_id: UUID,
       secondary_category_ids: List[UUID],  # NEW
       ai_suggested_category: Optional[UUID],
       ai_confidence: Optional[float],
       user_id: UUID,
       session: Session
   )
   ```

2. **`_load_config()`** - Pull all settings from database
3. **`_load_stopwords()`** - Load from database by language
4. **`_filter_quality_keywords()`** - Apply stopwords + length checks
5. **`_calculate_weight_adjustment()`** - Implement smart formula
6. **`_ensure_differential()`** - Preserve 0.3 minimum gap
7. **`_apply_weight_update()`** - Update or create CategoryKeyword records

**Step 3: Integration Points**
Update calls to ML service in:
- `document_upload_service.py::confirm_upload()` ✓ (already calls ML service)
- Document reclassification endpoints (if exists)
- Category update endpoints (if exists)

**Step 4: Testing & Validation**
1. Test single category classification
2. Test multi-category classification
3. Test overlap detection and differential preservation
4. Verify stopwords are filtered
5. Check accuracy metrics improve over time

### 🔄 Migration from Old to New System

**Backward Compatibility:**
- Keep existing `CategoryTrainingData` logs (valuable historical data)
- Existing keyword weights remain valid (we just learn smarter going forward)
- Existing `learn_from_decision()` calls will be updated to new signature

**Data Migration:**
- No data migration needed
- Existing keywords and weights work with new system
- New parameters start from defaults in `system_settings`

---

## 15. Future Enhancements

### Phase 2
- **User-Specific Learning**: Each user trains their personal model
- **Temporal Decay**: Old patterns slowly fade
- **Semantic Clustering**: Group similar keywords
- **N-gram Support**: Learn from phrases

### Phase 3
- **Active Learning**: System asks for help on ambiguous cases
- **Transfer Learning**: New users benefit from aggregate patterns
- **Explainable AI**: Show why prediction was made

---

## 16. Conclusion

This ML system makes Bonifatus DMS continuously smarter with every document. The key innovations are:

1. ✅ **Simple primary/secondary model** - no complex ordering
2. ✅ **Aggressive error correction** - wrong predictions get +0.5 boost
3. ✅ **Conservative reinforcement** - correct predictions get +0.2 bonus
4. ✅ **Differential preservation** - maintain 0.3 gap for clear winners
5. ✅ **No punishment** - never reduce weights, only boost correct categories
6. ✅ **Configurable** - all parameters tunable via settings

**The Result**: A self-improving classification system that gets better with use, minimizes overlaps, and maintains clear category boundaries.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Status**: Implementation Ready
