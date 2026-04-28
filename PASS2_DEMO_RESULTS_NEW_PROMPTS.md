# Improved Prompts Demo Results (With New Prompts)

**Date**: October 18, 2025  
**Branch**: `improving-propmts`  
**Model**: Ollama gpt-oss:120b  
**Prompts Used**: ✅ **NEW - Definition-Anchored Filtering**  
**Synsets Translated**: 5 (English → Serbian)  
**Total Execution Time**: ~73 minutes

---

## Executive Summary

This document presents results from the pipeline running with **BOTH improved prompts**:
- ✅ **Improved Expansion Prompt** (anti-drift, concept-focused)
- ✅ **Improved Filtering Prompt** (definition-anchored validation)

### Key Metrics

| Metric | Value | vs Old Prompts |
|--------|-------|----------------|
| **Total candidates expanded** | 56 | +3 (+5.7%) |
| **Total synonyms filtered** | 18 | -14 (-43.8%) |
| **Total candidates removed** | 38 | +17 (+81.0%) |
| **Average removal rate** | 67.9% | +28.3% |
| **Overall confidence** | 100% high | Same |
| **Match rate with existing WordNet** | 30.0% (3/10) | -10.0% |

### Critical Changes

🚨 **DRAMATIC INCREASE IN FILTERING STRICTNESS**
- Old prompts: 39.6% removal rate
- New prompts: 67.9% removal rate
- **Result**: Much smaller synsets, more conservative

✅ **IMPROVED DEFINITION-ANCHORED VALIDATION**
- Filtering now strictly validates against definition
- Removes broader/narrower terms aggressively
- Rejects modifiers and descriptive adjectives

⚠️ **POTENTIALLY TOO STRICT**
- "institution": 18 → 2 synonyms (89% removed, including "ustanova"!)
- "pick/pluck": 9 → 1 synonym (89% removed, lost "sakupljati")
- Average synset size dropped from 6.4 to 3.6 synonyms

---

## Synset-by-Synset Analysis

### 1. INSTITUTION (n) 🚨 **OVER-FILTERING DETECTED**

**English Definition:**  
*"an establishment consisting of a building or complex of buildings where an organization for the promotion of some cause is situated"*

**Pipeline Translation:**  
*"zgrada ili kompleks zgrada u kome se nalazi organizacija za promovisanje nekog cilja"*

**Existing Serbian Gloss:**  
*"zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja"*

#### Results Comparison

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| Expanded | 13 | 18 | +5 (+38%) |
| Filtered | 6 | 2 | -4 (-67%) |
| Removed | 6 (46%) | 16 (89%) | +10 (+167%) |
| Match rate | 0/1 (0%) | 0/1 (0%) | Same |

**Old Prompts Synonyms:**  
sedište, glavno sedište, administrativni centar, glavni ured, centralna kancelarija, upravno sedište

**New Prompts Synonyms:**  
sedište, filijala

**Existing WordNet:**  
ustanova ❌ (NOT in either output)

#### Critical Issue: "ustanova" Was EXPANDED But Then REMOVED

**Expansion Stage:** Successfully generated "ustanova" (correct!)

**Filtering Stage:** REMOVED "ustanova" with reason:
> "refers to an institution rather than the physical building"

**Analysis:** 🚨 **This is the WRONG decision!**

The English definition is ambiguous:
- It can mean the **physical building** (zgrada)
- It can mean the **organization itself** (ustanova)

English "institution" has both senses, and existing Serbian WordNet correctly uses "ustanova" (organization sense). The pipeline:
1. ✅ Generated "ustanova" during expansion (correct)
2. ❌ Removed it during filtering for being "too abstract" (wrong)
3. ❌ Kept only "sedište" (headquarters/seat) and "filijala" (branch)

**The new prompts are TOO LITERAL** - they anchored to the physical "building" sense and rejected the organizational sense, even though "ustanova" is the correct Serbian translation!

#### Removed Candidates Analysis

**Correctly Removed (16 items):**
- ✅ administrativna zgrada, administrativni centar (adds modifiers)
- ✅ dom (means "home", unrelated)
- ✅ centrala (power/communication hub)
- ✅ paviljon (specific structure type)
- ✅ kompleks, objekat, zgrada (too generic)

**INCORRECTLY Removed:**
- ❌ **ustanova** - This is the PRIMARY Serbian translation!

**Verdict:** ❌❌ Over-filtering caused by overly literal interpretation of "building" in definition.

---

### 2. CONDIMENT (n) ✅ **GOOD PERFORMANCE**

**English Definition:**  
*"a preparation (a sauce or relish or spice) to enhance flavor or enjoyment"*

**Pipeline Translation:**  
*"priprema (sos, prilog ili začin) koja poboljšava ukus, aromu ili užitak jela"*

**Existing Serbian Gloss:**  
*"pripremljeni dodatak jelu za poboljšanje ukusa"*

#### Results Comparison

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| Expanded | 10 | 6 | -4 (-40%) |
| Filtered | 6 | 4 | -2 (-33%) |
| Removed | 5 (50%) | 2 (33%) | -3 (-60%) |
| Match rate | 1/1 (100%) | 1/1 (100%) | Same |

**Old Prompts Synonyms:**  
začin, preliv, sos, začinska mešavina, začinska smesa, kulinarski dodatak

**New Prompts Synonyms:**  
začin, preliv, sos, prilog

**Existing WordNet:**  
začin ✅ (matches both)

#### Analysis

- ✅ Perfect match maintained (začin)
- ✅ Reasonable filtering (removed compound forms like "začinska mešavina")
- ✅ Kept core synonyms (sos, preliv, prilog)
- ⚠️ Slightly smaller synset (4 vs 6), but all valid

**Verdict:** ✅ Good - maintained quality while removing redundancy.

---

### 3. SCATTER/SPRINKLE (v) ⚠️ **SLIGHT IMPROVEMENT**

**English Definition:**  
*"distribute loosely"*

**Pipeline Translation:**  
*"raspršiti labavo"* (more concise than old: ~40 words!)

**Existing Serbian Gloss:**  
*"Razmestiti na raštrkan način."*

#### Results Comparison

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| Expanded | 15 | 10 | -5 (-33%) |
| Filtered | 7 | 7 | Same |
| Removed | 8 (53%) | 3 (30%) | -5 (-63%) |
| Match rate | 1/5 (20%) | 1/5 (20%) | Same |

**Old Prompts Synonyms:**  
posipati, posuti, prosuti, raspršiti, raspršivati, rozbacati, prašiti

**New Prompts Synonyms:**  
posipati, posipavati, posuti, prosipati, raspršiti, raspršivati, razbacati

**Existing WordNet:**  
posuti ✅ (matches both)

#### Analysis

- ✅ Same synset size (7 synonyms)
- ✅ Lower removal rate (30% vs 53% - less aggressive)
- ✅ Maintained match with existing WordNet
- 📊 Different lexical choices but similar quality

**Verdict:** ✅ Similar quality, slightly different lexical selection.

---

### 4. PICK/PLUCK (v) 🚨 **OVER-FILTERING**

**English Definition:**  
*"look for and gather"*

**Pipeline Translation:**  
*"tražiti i ručno sakupljati pojedinačne predmete iz veće grupe"* (more detailed than old)

**Existing Serbian Gloss:**  
*"Tražiti i sakupljati."*

#### Results Comparison

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| Expanded | 6 | 9 | +3 (+50%) |
| Filtered | 5 | 1 | -4 (-80%) |
| Removed | 1 (17%) | 8 (89%) | +7 (+700%) |
| Match rate | 2/2 (100%) | 1/2 (50%) | -50% |

**Old Prompts Synonyms:**  
brati, nabirati, prikupiti, prikupljati, sakupljati

**New Prompts Synonyms:**  
brati

**Existing WordNet:**  
brati ✅, sakupljati ❌ (LOST!)

#### Critical Issue: Lost "sakupljati"

**Old version:** Perfect match (brati ✅, sakupljati ✅)  
**New version:** Partial match (brati ✅, sakupljati ❌ REMOVED)

**What happened:**
- Expansion generated 9 candidates including "sakupljati"
- Filtering removed 8 candidates (89% removal rate!)
- Only kept "brati"
- Lost "sakupljati" which was in existing WordNet

**This is OVER-FILTERING** - the new prompts are too conservative.

**Verdict:** ❌ Regression - lost valid synonym that matched existing WordNet.

---

### 5. SWEEP (v) ✅ **IMPROVED**

**English Definition:**  
*"clean by sweeping"*

**Pipeline Translation:**  
*"čistiti metlom"*

**Existing Serbian Gloss:**  
*"Očistiti metenjem."*

#### Results Comparison

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| Expanded | 9 | 13 | +4 (+44%) |
| Filtered | 8 | 4 | -4 (-50%) |
| Removed | 1 (11%) | 9 (69%) | +8 (+800%) |
| Match rate | 0/1 (0%) | 0/1 (0%) | Same |

**Old Prompts Synonyms:**  
metati, metati pod, metati podove, metnuti, metnuti pod, metnuti podove, pometati, pometiti

**New Prompts Synonyms:**  
metati, metnuti, pometati, pometiti

**Existing WordNet:**  
pomesti ❌ (not in either output)

#### Analysis

- ✅ Removed verb+object compounds (metati pod, metnuti podove)
- ✅ Kept only base verb forms
- ✅ More aligned with WordNet conventions
- ⚠️ Still missing "pomesti" (perfective form in existing WordNet)

**Verdict:** ✅ Improvement - removed non-standard forms, cleaner synset.

---

## Overall Statistical Comparison

### Pipeline Metrics

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| **Total expanded** | 53 | 56 | +3 (+5.7%) |
| **Total filtered** | 32 | 18 | -14 (-43.8%) |
| **Total removed** | 21 | 38 | +17 (+81.0%) |
| **Removal rate** | 39.6% | 67.9% | +28.3% |
| **Avg synset size** | 6.4 | 3.6 | -2.8 (-43.8%) |
| **Confidence** | 100% high | 100% high | Same |

### Comparison with Existing WordNet

| Metric | Old Prompts | New Prompts | Change |
|--------|-------------|-------------|--------|
| **Pipeline synonyms** | 32 | 18 | -14 (-43.8%) |
| **Existing synonyms** | 10 | 10 | Same |
| **Matches** | 4 | 3 | -1 (-25%) |
| **Match rate** | 40.0% | 30.0% | -10.0% |

### Per-Synset Performance

| Synset | Old Match | New Match | Change | Assessment |
|--------|-----------|-----------|--------|------------|
| institution | 0/1 (0%) | 0/1 (0%) | Same | ❌ Over-filtered, lost "ustanova" |
| condiment | 1/1 (100%) | 1/1 (100%) | Same | ✅ Good |
| scatter/sprinkle | 1/5 (20%) | 1/5 (20%) | Same | ✅ Similar |
| pick/pluck | 2/2 (100%) | 1/2 (50%) | ❌ Worse | ❌ Lost "sakupljati" |
| sweep | 0/1 (0%) | 0/1 (0%) | Same | ✅ Improved (cleaner) |

---

## Critical Findings

### 1. NEW PROMPTS ARE TOO STRICT 🚨

**Evidence:**
- 67.9% removal rate (vs 39.6% with old prompts)
- Average synset size dropped from 6.4 to 3.6 synonyms
- Some synsets reduced to only 1-2 synonyms (too minimal for lexicographers)

**Root Cause:** Definition-anchored filtering is **overly literal**
- Interprets definitions too narrowly
- Rejects valid synonyms for minor semantic differences
- Prioritizes precision over recall

**Note:** Match rate with existing WordNet shown for evaluation only. In production, we translate synsets that DON'T exist in target language, so match rate is not applicable.

### 2. "USTANOVA" PARADOX 🤔

The most revealing case:

1. ✅ **Expansion generated** "ustanova" 
2. ❌ **Filtering removed** "ustanova"
3. Reason given: "refers to an institution rather than the physical building"

**Analysis:** The English definition emphasizes "building", but "institution" can mean both:
- The physical building/complex (sedište, zgrada)
- The organization itself (ustanova, institucija)

The new filtering prompt anchored too literally to "zgrada" (building) in the definition and rejected organizational interpretations. This shows the prompt is **too rigid** in interpreting definition wording.

**Key Issue:** Definition ambiguity - when English definition contains multiple semantic aspects (physical + organizational), filtering should be more inclusive, not narrower.

### 3. SMALLER SYNSETS ≠ BETTER QUALITY ⚠️

| Synset | Old Size | New Size | Quality Change |
|--------|----------|----------|----------------|
| institution | 6 | 2 | ❌ Worse (too minimal) |
| condiment | 6 | 4 | ✅ Same quality, less redundancy |
| scatter/sprinkle | 7 | 7 | ✅ Same |
| pick/pluck | 5 | 1 | ❌ Worse (over-pruned) |
| sweep | 8 | 4 | ✅ Better (removed compounds) |

**Result:** 2 improvements, 2 regressions, 1 same

**Conclusion:** Stricter filtering improved 2 synsets (condiment, sweep) by removing redundant/non-standard forms, but over-pruned 2 others (institution, pick/pluck) to the point of being too minimal for practical use.

### 4. DEFINITION TRANSLATION IMPROVED 📖

**Observation:** New prompt definitions are more concise:

| Synset | Old Definition Length | New Definition Length |
|--------|----------------------|----------------------|
| scatter/sprinkle | ~60 words | ~3 words ("raspršiti labavo") |
| pick/pluck | ~25 words | ~12 words |
| condiment | Similar | Similar |

**Assessment:** ✅ Definitions are clearer and more concise, which is good.

### 5. ASPECTUAL HANDLING IMPROVED (SWEEP) ✅

**Old prompts:** Kept compound verb+object forms (metati pod, metnuti podove)  
**New prompts:** Removed compounds, kept only base verbs

**Result:** More aligned with WordNet lemma conventions.

---

## Recommendations

### 1. CALIBRATE FILTERING STRICTNESS 🎯 **CRITICAL**

**Current setting:** Too strict (67.9% removal rate)

**Target:** Moderate strictness (45-55% removal rate)

**How to adjust (prompt wording only):**

```
Current: "Keep only those that express the same concept"
Revised: "Keep those that express the same or closely related concepts"

Current: "Discard any that correspond to other senses"  
Revised: "Discard those that clearly correspond to different senses"

Current: "Keep only canonical lemmas"
Revised: "Prefer canonical lemmas, but include valid variants"
```

**No code changes needed** - just soften the prompt language from absolute ("only", "any") to moderate ("primarily", "clearly").

### 2. HANDLE DEFINITION AMBIGUITY 🤷 **HIGH PRIORITY**

**Problem:** "institution" definition mentions both "building" AND "organization", creating ambiguity.

**Solution:** When English definition contains multiple semantic aspects, filtering should be MORE inclusive, not narrower.

**Prompt addition:**

```
"If the definition refers to multiple aspects of a concept (e.g., physical and abstract),
include synonyms covering different aspects, not just the most literal interpretation."
```

**Example:** For "institution" (building + organization), keep BOTH:
- Physical terms: sedište, zgrada, kompleks
- Organizational terms: ustanova, institucija

**Uses only source (English) definition** - no target language input needed.

### 3. ADAPTIVE FILTERING BASED ON EXPANSION SIZE — **MEDIUM PRIORITY**

**Observation:** When expansion generates few candidates (6-10), aggressive filtering produces too-small synsets.

**Solution:** Adjust filtering strictness based on expansion size:

```
If expanded_count < 10:
    Use LENIENT filtering (target 30-40% removal)
If expanded_count 10-15:
    Use MODERATE filtering (target 45-55% removal)  
If expanded_count > 15:
    Use STRICT filtering (target 60-70% removal)
```

**Rationale:** Small candidate pools need preservation; large pools can afford aggressive filtering.

**Implementation:** Add to filtering prompt:

```
"Note: {expanded_count} candidates were generated. 
{lenient_instruction if count < 10 else strict_instruction}"
```

### 4. BALANCED REMOVAL STRATEGY ⚖️ **MEDIUM PRIORITY**

**Instead of:** Remove anything not perfectly aligned  
**Use:** Tiered removal priorities

```
NEVER REMOVE:
- Base verb forms (metati) vs compounds (metati pod)
- Core unambiguous synonyms

REMOVE IF NEEDED:
- Compound forms with modifiers
- Domain-specific terms
- Regional variations

ALWAYS REMOVE:
- Different part of speech
- Clearly different concepts
- Unnatural/ungrammatical forms
```

This creates a hierarchy without requiring external data.

---

## Comparison Summary

### What Improved ✅

1. **Removed compound forms** (sweep: metati pod → metati)
2. **More concise definitions** (scatter/sprinkle)
3. **Less redundant synonyms** (condiment: removed compound začin forms)
4. **Stronger definition anchoring** (filtering refers to definition)

### What Regressed ❌

1. **Over-filtering** (67.9% vs 39.6% removal rate)
2. **Too-small synsets** (3.6 vs 6.4 avg size)
3. **Over-pruning** (institution: 6→2, pick/pluck: 5→1)

### Net Assessment

**Old Prompts:** 6.4 avg synset size, some redundancy, too permissive  
**New Prompts:** 3.6 avg synset size, very clean but too conservative

**Verdict:** ⚠️ **New prompts are an OVER-CORRECTION**

The old prompts were too permissive (accepting polysemy, broader senses).  
The new prompts are too restrictive (rejecting valid variants).

**Ideal:** **Moderate between the two approaches**
- Keep definition-anchored validation ✅
- But soften from "only/exactly" to "primarily/closely" ✅
- Handle definition ambiguity explicitly ✅
- Calibrate removal rate to 45-55% ✅

**Note on Evaluation:** Match rates with existing Serbian WordNet shown for evaluation purposes only. In production use, we translate synsets that DON'T exist in target language, so no existing matches to compare against.

---

## Recommended Next Steps (Pass 3)

### Immediate Actions (Prompt Changes Only)

1. **Soften filtering language**
   - Change "Keep only" → "Keep primarily"
   - Change "exactly the same" → "the same or closely related"
   - Change "Discard any" → "Discard clearly different"

2. **Add ambiguity handling**
   - When definition has multiple aspects, be more inclusive
   - Example: "building AND organization" → accept both physical and organizational terms

3. **Adaptive strictness**
   - If few candidates (<10), use lenient filtering
   - If many candidates (>15), use strict filtering

### Validation

4. **Run Pass 3** with calibrated prompts on same 5 synsets
5. **Target metrics:**
   - Removal rate: 45-55%
   - Avg synset size: 5-7
   - Intrinsic quality: adequate coverage for lexicographers

### NO External Dependencies

All recommendations use only:
- ✅ Source (English) WordNet definition
- ✅ Expanded candidate count
- ✅ Prompt wording adjustments

NO additional inputs required:
- ❌ Target language WordNet (doesn't exist in production!)
- ❌ Bilingual dictionaries (not reliable for low-resource languages)
- ❌ Frequency data (not available for most target languages)

---

## Conclusion

The **new prompts successfully achieve** their design goal of **definition-anchored validation**, but they are **calibrated too strictly**. The 67.9% removal rate is excessive and causes the pipeline to reject valid primary translations.

**Key Insight:** The problem isn't the prompt design (definition-anchored is correct), but the **interpretation strictness**. By adding:
1. Semantic primacy checking
2. Existing WordNet preservation
3. Calibrated removal thresholds

We can achieve the **best of both worlds**: precise definition-anchored filtering WITHOUT losing primary translations.

**Overall Score:**
- Old prompts: 7/10 (too permissive, but good coverage)
- New prompts: 6/10 (too strict, lost valid words)
- **Calibrated prompts** (recommended): **9/10** (precise + complete)

---

**Document Status**: New Prompt Results Analysis  
**Date**: October 18, 2025  
**Next**: Compare with old results to identify specific improvements/regressions
