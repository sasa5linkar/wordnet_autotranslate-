# Pass 1 vs Pass 2 Comparison

**Analysis Date**: October 18-19, 2025  
**Branch**: `improving-propmts`  
**Documents Compared**:
- PASS 1: `PASS1_DEMO_ANALYSIS_OLD_PROMPTS.md` (naturalness-first filtering)
- PASS 2: `PASS2_DEMO_RESULTS_NEW_PROMPTS.md` (definition-anchored filtering)

---

## Executive Comparison

### High-Level Metrics

| Metric | PASS 1 | PASS 2 | Change | Interpretation |
|--------|--------|--------|--------|----------------|
| **Total expanded** | 53 | 56 | +3 (+5.7%) | ✅ Slightly more comprehensive expansion |
| **Total filtered** | 32 | 18 | -14 (-43.8%) | ❌ **Dramatic reduction in synset size** |
| **Total removed** | 21 | 38 | +17 (+81.0%) | ❌ **Much more aggressive filtering** |
| **Removal rate** | 39.6% | 67.9% | +28.3 pp | ❌ **Over-correction** |
| **Avg synset size** | 6.4 | 3.6 | -2.8 (-43.8%) | ❌ **Synsets too small** |
| **Eval match rate** | 40.0% (4/10) | 30.0% (3/10) | -10.0 pp | ⚠️ For evaluation only |
| **Confidence** | 100% high | 100% high | Same | ⚠️ Needs calibration |

### Summary

🚨 **PASS 2 PROMPTS ARE TOO STRICT**
- Removal rate increased by 71% (39.6% → 67.9%)
- Average synset size decreased by 44% (6.4 → 3.6 synonyms)
- Two synsets reduced to 1-2 words (too minimal)

**Note on Match Rate:** Shown for evaluation purposes only. In production, pipeline translates synsets that DON'T exist in target language WordNet, so no existing matches to compare against.

---

## Synset-by-Synset Comparison

### 1. INSTITUTION

| Metric | OLD | NEW | Change | Winner |
|--------|-----|-----|--------|--------|
| Expanded | 13 | 18 | +5 (+38%) | NEW |
| Filtered | 6 | 2 | -4 (-67%) | OLD |
| Removed | 6 (46%) | 16 (89%) | +10 | OLD |
| Match rate | 0/1 (0%) | 0/1 (0%) | Same | TIE |

**OLD Synonyms:**  
sedište, glavno sedište, administrativni centar, glavni ured, centralna kancelarija, upravno sedište

**NEW Synonyms:**  
sedište, filijala

**Existing WordNet:**  
ustanova ❌

**KEY FINDING:** 🚨 **NEW prompts REMOVED "ustanova" after generating it!**

OLD prompts never generated "ustanova" (sense drift to "headquarters").  
NEW prompts generated "ustanova" during expansion ✅ but then removed it during filtering ❌ with reason: *"refers to an institution rather than the physical building"*.

**Problem:** Both versions miss the correct sense, but NEW version is worse because it:
1. Generated the correct word ✅
2. Then rejected it ❌

**Winner:** OLD (less wrong - at least didn't generate then remove correct word)

---

### 2. CONDIMENT

| Metric | OLD | NEW | Change | Winner |
|--------|-----|-----|--------|--------|
| Expanded | 10 | 6 | -4 (-40%) | TIE |
| Filtered | 6 | 4 | -2 (-33%) | TIE |
| Removed | 5 (50%) | 2 (33%) | -3 | NEW |
| Match rate | 1/1 (100%) | 1/1 (100%) | Same | TIE |

**OLD Synonyms:**  
začin, preliv, sos, začinska mešavina, začinska smesa, kulinarski dodatak

**NEW Synonyms:**  
začin, preliv, sos, prilog

**Existing WordNet:**  
začin ✅

**Analysis:**
- Both maintain perfect match with existing WordNet
- NEW removes compound forms (začinska mešavina, začinska smesa) ✅
- NEW has slightly cleaner synset (4 vs 6) ✅
- Both are high quality

**Winner:** NEW (cleaner, less redundancy)

---

### 3. SCATTER/SPRINKLE

| Metric | OLD | NEW | Change | Winner |
|--------|-----|-----|--------|--------|
| Expanded | 15 | 10 | -5 (-33%) | TIE |
| Filtered | 7 | 7 | Same | TIE |
| Removed | 8 (53%) | 3 (30%) | -5 | NEW |
| Match rate | 1/5 (20%) | 1/5 (20%) | Same | TIE |

**OLD Synonyms:**  
posipati, posuti, prosuti, raspršiti, raspršivati, rozbacati, prašiti

**NEW Synonyms:**  
posipati, posipavati, posuti, prosipati, raspršiti, raspršivati, razbacati

**Existing WordNet:**  
posuti ✅

**Analysis:**
- Same synset size (7 synonyms)
- Both maintain match with existing WordNet
- Different lexical choices but similar quality
- NEW has lower removal rate (30% vs 53%), indicating better expansion quality

**Winner:** TIE (different but equally valid)

---

### 4. PICK/PLUCK

| Metric | OLD | NEW | Change | Winner |
|--------|-----|-----|--------|--------|
| Expanded | 6 | 9 | +3 (+50%) | NEW |
| Filtered | 5 | 1 | -4 (-80%) | OLD |
| Removed | 1 (17%) | 8 (89%) | +7 | OLD |
| Match rate | 2/2 (100%) | 1/2 (50%) | -50% | OLD |

**OLD Synonyms:**  
brati, nabirati, prikupiti, prikupljati, sakupljati

**NEW Synonyms:**  
brati

**Existing WordNet:**  
brati ✅, sakupljati ❌ (LOST in NEW)

**KEY FINDING:** 🚨 **NEW prompts LOST "sakupljati"**

OLD prompts: Perfect match (2/2) with existing WordNet  
NEW prompts: Partial match (1/2) - lost "sakupljati"

**This is a CLEAR REGRESSION**

**Winner:** OLD (maintained complete match with existing WordNet)

---

### 5. SWEEP

| Metric | OLD | NEW | Change | Winner |
|--------|-----|-----|--------|--------|
| Expanded | 9 | 13 | +4 (+44%) | NEW |
| Filtered | 8 | 4 | -4 (-50%) | NEW |
| Removed | 1 (11%) | 9 (69%) | +8 | NEW |
| Match rate | 0/1 (0%) | 0/1 (0%) | Same | TIE |

**OLD Synonyms:**  
metati, metati pod, metati podove, metnuti, metnuti pod, metnuti podove, pometati, pometiti

**NEW Synonyms:**  
metati, metnuti, pometati, pometiti

**Existing WordNet:**  
pomesti ❌

**Analysis:**
- OLD kept compound verb+object forms (metati pod, metnuti podove) ❌
- NEW removed compounds, kept only base verbs ✅
- NEW is more aligned with WordNet lemma conventions ✅
- Neither matches existing WordNet (both missing "pomesti")

**Winner:** NEW (cleaner, more standard forms)

---

## Scorecard

### Per-Synset Winners

| Synset | Winner | Reason |
|--------|--------|--------|
| institution | PASS 1 | PASS 2 generated then removed valid synonym |
| condiment | PASS 2 | Cleaner, removed redundancy |
| scatter/sprinkle | TIE | Different but equally valid |
| pick/pluck | PASS 1 | Better coverage (4 valid synonyms vs 1) |
| sweep | PASS 2 | Removed non-standard compound forms |

**Overall:** PASS 1: 2 wins, PASS 2: 2 wins, 1 tie

**Note:** Evaluation used existing Serbian WordNet for reference only. Production use translates synsets WITHOUT existing target language data.

---

## Critical Differences

### 1. FILTERING PHILOSOPHY

**OLD Prompts:**
- "Preserve the core concept but prefer natural, idiomatic expressions"
- "Include abstract or concrete variants when native speakers conceptualize that way"
- "Prioritize native semantic norms over literal translation"
- **Result:** Inclusive, sometimes too permissive

**NEW Prompts:**
- "Evaluate each candidate strictly against this definition"
- "Keep only those that express the same concept described in the definition"
- "Reject any forms adding descriptive modifiers or particles"
- "Keep only canonical lemmas expressing exactly this sense"
- **Result:** Strict, sometimes too conservative

### 2. THE "USTANOVA" PARADOX

**Most revealing case study:**

OLD version:
- Never generated "ustanova" (focused on "headquarters" sense)
- 0% match with existing WordNet
- Wrong sense, but internally consistent

NEW version:
- ✅ Generated "ustanova" during expansion (correct!)
- ❌ Removed "ustanova" during filtering (wrong!)
- Reason given: "refers to an institution rather than the physical building"
- **This is worse because it HAD the right answer then threw it away**

**Root cause:** NEW prompts anchor too literally to definition wording ("building or complex of buildings") and reject valid abstract/organizational senses.

### 3. REMOVAL RATE TRAJECTORY

| Stage | OLD Removal Rate | NEW Removal Rate | Interpretation |
|-------|------------------|------------------|----------------|
| institution | 46% | 89% | NEW too aggressive |
| condiment | 50% | 33% | NEW more balanced |
| scatter/sprinkle | 53% | 30% | NEW less aggressive (good) |
| pick/pluck | 17% | 89% | NEW WAY too aggressive |
| sweep | 11% | 69% | NEW much more aggressive |
| **Average** | **39.6%** | **67.9%** | **NEW over-corrected** |

**Pattern:** NEW prompts are inconsistent:
- Sometimes just right (condiment, scatter)
- Sometimes way too strict (institution, pick/pluck)

### 4. SMALLER SYNSET SIZES IN PASS 2

**PASS 1 average synset size:** 6.4 synonyms
**PASS 2 average synset size:** 3.6 synonyms

**Some synsets too minimal:**
- institution: 1 synonym (instalacija) - too minimal for lexicographers
- pick/pluck: 1 synonym (brati) - lost other valid synonyms (sakupljati, nabirati, etc.)

**Evaluation Note:** Match rate shown for reference only. In production, no existing target WordNet to compare against.

---

## What Worked vs What Didn't

### ✅ What NEW Prompts Improved

1. **Removed compound forms** (sweep)
   - OLD: metati pod, metati podove, metnuti pod, metnuti podove ❌
   - NEW: metati, metnuti, pometati, pometiti ✅

2. **Removed redundant compound synonyms** (condiment)
   - OLD: začinska mešavina, začinska smesa ❌
   - NEW: (removed these) ✅

3. **More concise definitions**
   - scatter/sprinkle OLD: ~60 words
   - scatter/sprinkle NEW: ~3 words ("raspršiti labavo")

4. **Stronger definition anchoring**
   - Filtering explicitly refers to definition
   - Removal reasons cite definition mismatch

### ❌ What PASS 2 Prompts Overcorrected

1. **Over-aggressive filtering**
   - 67.9% removal rate (vs 39.6%)
   - Average synset size: 3.6 (vs 6.4)
   - Some synsets down to 1-2 synonyms (too minimal for practical use)

2. **Lost valid synonyms**
   - sakupljati, nabirati, prikupiti, prikupljati (pick/pluck) - removed due to strict interpretation
   - ustanova (institution) - generated then removed due to definition ambiguity

3. **Overly literal interpretation**
   - Focused on "building" in definition, rejected "institution" (organization/establishment)
   - Rejected valid abstract/organizational senses

4. **Inconsistent strictness**
   - condiment: 33% removal (reasonable)
   - institution: 89% removal (excessive)
   - pick/pluck: 89% removal (excessive)

---

## Root Cause Analysis

### Why Did NEW Prompts Over-Filter?

**The new filtering prompt says:**
> "Keep only those that express the **same concept** described in the definition"
> "Discard any that correspond to **other senses** of the same word"

**Problem:** This is interpreted as:
- "same" = identical, not similar
- "other senses" = any variation, even valid ones

**Solution needed:**
```diff
- "Keep only those that express the same concept"
+ "Keep those that express the same or closely related concepts"

- "Discard any that correspond to other senses"
+ "Discard any that correspond to clearly different senses"

+ "Include core synonyms even if they emphasize different aspects"
+ "Preserve primary translations in the target language"
```

### Why Did "ustanova" Get Removed?

**Definition:** "a building or complex of buildings where an organization... is situated"

**Filtering logic in PASS 2:**
1. Definition mentions "building" (physical) ✓
2. "ustanova" means "institution" (organizational) ✓
3. Therefore "ustanova" ≠ "building"
4. Remove "ustanova" ❌

**Root Cause:** English "institution" has multiple aspects:
- The physical building (sede, sedište)
- The organization itself (ustanova)

The pipeline's overly literal interpretation of "building or complex of buildings" led it to reject a valid synonym focusing on the organizational aspect.

**Solution:** When definitions have multiple aspects (physical + organizational), prompts should be more inclusive of synonyms emphasizing different aspects. This is a **prompt wording issue**, not a code issue. No external data needed.

---

## Quantitative Comparison

### Size Comparison

| Synset | OLD Size | NEW Size | Change | Quality |
|--------|----------|----------|--------|---------|
| institution | 6 | 2 | -67% | ❌ Too small |
| condiment | 6 | 4 | -33% | ✅ Good |
| scatter/sprinkle | 7 | 7 | 0% | ✅ Same |
| pick/pluck | 5 | 1 | -80% | ❌ Way too small |
| sweep | 8 | 4 | -50% | ✅ Better |
| **Average** | **6.4** | **3.6** | **-44%** | ⚠️ **Too small** |

**Ideal range:** 4-8 synonyms per synset  
**OLD average:** 6.4 ✅ (good)  
**NEW average:** 3.6 ❌ (too small)

### Quality Comparison (Intrinsic Metrics)

| Metric | PASS 1 | PASS 2 | Change |
|--------|--------|--------|--------|
| Average synset size | 6.4 | 3.6 | -2.8 (❌) |
| Removal rate | 39.6% | 67.9% | +28.3% (❌) |
| Synsets < 3 words | 0/5 | 2/5 | +2 (❌) |
| Compound forms removed | Partial | Complete | ✅ |
| Verb+object removed | No | Yes | ✅ |

**Summary:** PASS 2 better at removing non-standard forms, but too aggressive overall (synsets too small).

**Evaluation Note:** Match rates with existing Serbian WordNet shown for reference only. In production use, pipeline translates synsets that DON'T exist in target language, so no matches to preserve.

---

## Recommendations for Pass 3 (Calibrated Approach)

### 1. RECALIBRATE FILTERING STRICTNESS 🎯 **CRITICAL**

**Target metrics:**
- Removal rate: 45-55% (between Pass 1's 39.6% and Pass 2's 67.9%)
- Average synset size: 5-7 synonyms (between 3.6 and 6.4)
- Maintain compound/modifier removal (Pass 2's strength)

**Implementation:** Simple prompt wording changes (no code, no external data):
```diff
- "Keep only those that express the same concept"
+ "Keep those that express the same or closely related concepts"

- "Discard any that correspond to other senses"
+ "Discard any that correspond to clearly different senses"

+ "When definitions have multiple aspects (e.g., physical + organizational), 
   include synonyms emphasizing different aspects"
```

### 2. HANDLE DEFINITION AMBIGUITY 📖 **HIGH PRIORITY**

**Problem:** Some definitions (like "institution") mention multiple aspects:
- Physical (building)
- Organizational (establishment)

**Solution:** Prompt should guide LLM to be inclusive when source definition is multi-faceted.

**Implementation:** Add to filtering prompt:
```
"If the English definition describes multiple related aspects or components,
 include synonyms that emphasize any of these aspects, not just the literal one."
```

**Uses:** Only source English WordNet definition. No external data.

### 3. ADAPTIVE FILTERING BASED ON EXPANSION SIZE 🔄 **MEDIUM PRIORITY**

**Observation:** Pass 2 removed too many candidates when expansion was already small.

**Example:**
- pick/pluck: Only 9 candidates → Removed 8 → Left with 1 (too minimal)

**Solution:** Adjust filtering strictness based on candidate count:
- Large expansions (>15): Apply strict filtering
- Medium expansions (8-15): Apply moderate filtering  
- Small expansions (<8): Apply lenient filtering

**Implementation:** Add context to filtering prompt:
```
"There are {n} candidates to evaluate. 
 Aim to keep approximately {target_keep}% of them."
```

**Uses:** Intrinsic metric (candidate count). No external data.

### 4. BALANCED REMOVAL STRATEGY ⚖️ **MEDIUM PRIORITY**

**Current problem:** Inconsistent removal rates across synsets:
- institution: 89% removed
- pick/pluck: 89% removed
- condiment: 33% removed

**Solution:** Prompt should encourage balanced approach without hard thresholds:
```
"Aim for a balanced final synset - not too large (redundant), 
 not too small (incomplete). Typically 4-8 synonyms is appropriate."
```

**Uses:** Only intrinsic quality assessment. No external data.

---

## Implementation Path for Pass 3

All recommendations above require **ONLY prompt wording changes** - no code modifications, no external data sources, no new pipeline stages.

**Steps:**
1. Edit expansion prompt: Keep Pass 2's anti-drift guidelines
2. Edit filtering prompt: Soften language ("primarily" instead of "only")
3. Add definition ambiguity handling to filtering prompt
4. Add candidate count context to filtering prompt
5. Add balanced synset size guidance to filtering prompt

**Expected outcomes:**
- Removal rate: 45-55% (vs 67.9%)
- Average synset size: 5-7 (vs 3.6)
- Maintain compound/modifier removal (Pass 2's strength)
- Better handling of multi-faceted definitions

**No changes needed:**
- ❌ No code changes
- ❌ No new pipeline stages
- ❌ No external data sources (target WordNet, dictionaries, frequency data)
- ✅ Only prompt text modifications

---

## Final Verdict

### Numerical Score

**PASS 1 Prompts:** 7/10
- ✅ Good coverage (6.4 avg synonyms)
- ✅ Adequate synset sizes
- ❌ Too permissive (accepted polysemy)
- ❌ Kept non-standard forms

**PASS 2 Prompts:** 6/10
- ✅ Removes compounds/modifiers
- ✅ Definition-anchored (good concept)
- ❌ Too strict (67.9% removal)
- ❌ Over-filtering (3.6 avg synonyms)
- ❌ Some synsets too minimal (1-2 words)

**PASS 3 (Recommended - Calibrated):** Target 9/10
- ✅ Definition-anchored validation (keep from Pass 2)
- ✅ Remove compounds/modifiers (keep from Pass 2)
- ✅ Moderate removal rate (45-55%)
- ✅ Maintain coverage (5-7 avg synonyms)
- ✅ Handle definition ambiguity
- ✅ Uses ONLY source English WordNet (no target language input)

### Visual Comparison

```
Removal Rate:
PASS 1: ████████████████████████░░░░░░░░░░░░░░░░░░ 39.6%
PASS 2: ██████████████████████████████████████████ 67.9% ❌ TOO HIGH
PASS 3: ████████████████████████████░░░░░░░░░░░░░░ 50.0% ✅ TARGET

Synset Size:
PASS 1: ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░ 6.4 ✅
PASS 2: ███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 3.6 ❌ TOO SMALL
PASS 3: ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░ 5.5 ✅ TARGET
```

### Key Takeaway

**PASS 2 prompts overcorrected.** They successfully addressed the "too permissive" problem but created a "too restrictive" problem. The solution is NOT to go back to PASS 1, but to **calibrate between the two extremes**.

**Action for Pass 3:** Simple prompt wording changes (no code, no external data):
1. Soften language: "only" → "primarily", "exactly" → "closely"
2. Handle ambiguity: When definition has multiple aspects, be more inclusive
3. Adaptive strictness: Adjust based on candidate count

---

## Appendices

### A. Specific Lost Synonyms

| Synset | Lost in PASS 2 | Why Lost | Assessment |
|--------|----------------|----------|------------|
| institution | ustanova | Definition interpretation issue | ⚠️ Valid synonym, but definition ambiguous (institution vs building) |
| pick/pluck | sakupljati, nabirati, prikupiti, prikupljati | Over-aggressive filtering | ⚠️ Valid synonyms, filtering too strict |
| condiment | začinska mešavina, začinska smesa, kulinarski dodatak | Compound forms | ✅ Correctly removed - redundant compounds |
| sweep | metati pod, metnuti podove, etc. | Compound verb+object | ✅ Correctly removed - non-standard forms |

**Net:** Pass 2 filtering too strict for some synsets, but correctly removes compounds/modifiers.

### B. Expansion Quality

Both prompt versions generate good expansion candidates. The difference is in filtering strictness:

| Synset | PASS 1 Expanded | PASS 2 Expanded | Quality |
|--------|-----------------|-----------------|---------|
| institution | 13 | 18 | PASS 2 better (+5) |
| condiment | 10 | 6 | Both good |
| scatter/sprinkle | 15 | 10 | Both good |
| pick/pluck | 6 | 9 | PASS 2 better (+3) |
| sweep | 9 | 13 | PASS 2 better (+4) |

**Expansion winner:** PASS 2 (generates more candidates)  
**Filtering winner:** Neither (PASS 1 too lenient, PASS 2 too strict)

### C. Confidence Metric

Both PASS 1 and PASS 2 show 100% "high" confidence:
- PASS 1: 6.4 avg synonyms
- PASS 2: 3.6 avg synonyms

**Confidence metric doesn't reflect synset size** - may need intrinsic quality indicators.

---

**Document Status:** Comparative Analysis Complete  
**Recommendation:** Implement calibrated hybrid approach  
**Priority:** HIGH - Current NEW prompts are regressing quality
