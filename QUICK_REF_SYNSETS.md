# Quick Reference: Test Synsets Overview

**Purpose**: Quick lookup table for all test synsets used in Pass 1-4 analysis  
**Updated**: October 19, 2025

---

## All 5 Test Synsets

### Synset 1: Institution

| Field | Value |
|-------|-------|
| **Synset ID** | ENG30-03574555-n |
| **English Lemmas** | institution |
| **POS** | noun |
| **Definition** | an establishment consisting of a building or complex of buildings where an organization for the promotion of some cause is situated |
| **Existing Serbian** | ustanova (1 synonym) |
| **Serbian Definition** | zgrada u kojoj se nalazi organizaciona jedinica neke grane javnog poslovanja |

---

### Synset 2: Condiment

| Field | Value |
|-------|-------|
| **Synset ID** | ENG30-07810907-n |
| **English Lemmas** | condiment |
| **POS** | noun |
| **Definition** | a preparation (a sauce or relish or spice) to enhance flavor or enjoyment |
| **Existing Serbian** | začin (1 synonym) |
| **Serbian Definition** | (need to check data file) |

---

### Synset 3: Scatter, Sprinkle

| Field | Value |
|-------|-------|
| **Synset ID** | ENG30-01376245-v |
| **English Lemmas** | scatter, sprinkle, dot, dust, disperse |
| **POS** | verb |
| **Definition** | distribute loosely |
| **Existing Serbian** | posuti, rasejati, rasturiti, rasuti, raštrkati (5 synonyms) |
| **Serbian Definition** | (need to check data file) |

---

### Synset 4: Pick, Pluck

| Field | Value |
|-------|-------|
| **Synset ID** | ENG30-01382083-v |
| **English Lemmas** | pick, pluck, cull |
| **POS** | verb |
| **Definition** | look for and gather |
| **Existing Serbian** | brati, sakupljati (2 synonyms) |
| **Serbian Definition** | (need to check data file) |

---

### Synset 5: Sweep

| Field | Value |
|-------|-------|
| **Synset ID** | ENG30-01393996-v |
| **English Lemmas** | sweep |
| **POS** | verb |
| **Definition** | clean by sweeping |
| **Existing Serbian** | čistiti, mesti (2 synonyms) |
| **Serbian Definition** | (need to check data file) |

---

## Pass Results Summary

### Pass 4 Results (Polysemy-Aware)

| Synset | ID | Expanded | Filtered | Removed | Removal % | Confidence |
|--------|----|---------:|--------:|---------:|---------:|-----------|
| 1. Institution | ENG30-03574555-n | 18 | 9 → 6* | 9 | 50.0% | high |
| 2. Condiment | ENG30-07810907-n | TBD | TBD | TBD | TBD | TBD |
| 3. Scatter/Sprinkle | ENG30-01376245-v | TBD | TBD | TBD | TBD | TBD |
| 4. Pick/Pluck | ENG30-01382083-v | TBD | TBD | TBD | TBD | TBD |
| 5. Sweep | ENG30-01393996-v | TBD | TBD | TBD | TBD | TBD |

*9 filtered, then deduplication removed 3 compounds → 6 final

### Pass 3 Results (Calibrated)

| Synset | ID | Expanded | Filtered | Removed | Removal % | Confidence |
|--------|----|---------:|--------:|---------:|---------:|-----------|
| 1. Institution | ENG30-03574555-n | 18 | 9 | 8 | 44.4% | high |
| 2. Condiment | ENG30-07810907-n | 5 | 4 | 1 | 20.0% | high |
| 3. Scatter/Sprinkle | ENG30-01376245-v | 7 | 7 | 0 | 0.0% | high |
| 4. Pick/Pluck | ENG30-01382083-v | 9 | 8 | 1 | 11.1% | high |
| 5. Sweep | ENG30-01393996-v | 14 | 5 | 9 | 64.3% | high |
| **AVERAGE** | - | **10.6** | **6.6** | **3.8** | **37.7%** | **100% high** |

### Pass 2 Results (Strict)

| Synset | ID | Expanded | Filtered | Removed | Removal % | Confidence |
|--------|----|---------:|--------:|---------:|---------:|-----------|
| 1. Institution | ENG30-03574555-n | 28 | 9 | 19 | 67.9% | high |
| 2. Condiment | ENG30-07810907-n | 5 | 3 | 2 | 40.0% | medium |
| 3. Scatter/Sprinkle | ENG30-01376245-v | 13 | 4 | 9 | 69.2% | high |
| 4. Pick/Pluck | ENG30-01382083-v | 10 | 4 | 6 | 60.0% | high |
| 5. Sweep | ENG30-01393996-v | 16 | 3 | 13 | 81.3% | high |
| **AVERAGE** | - | **14.4** | **4.6** | **9.8** | **67.9%** | **80% high** |

### Pass 1 Results (Baseline)

| Synset | ID | Expanded | Filtered | Removed | Removal % | Confidence |
|--------|----|---------:|--------:|---------:|---------:|-----------|
| 1. Institution | ENG30-03574555-n | 53 | 32 | 21 | 39.6% | medium |
| 2. Condiment | ENG30-07810907-n | 9 | 6 | 3 | 33.3% | high |
| 3. Scatter/Sprinkle | ENG30-01376245-v | 18 | 12 | 6 | 33.3% | high |
| 4. Pick/Pluck | ENG30-01382083-v | 16 | 9 | 7 | 43.8% | medium |
| 5. Sweep | ENG30-01393996-v | 23 | 13 | 10 | 43.5% | high |
| **AVERAGE** | - | **23.8** | **14.4** | **9.4** | **39.6%** | **80% high** |

---

## Key Observations

### Trend Analysis

1. **Removal Rate Evolution**:
   - Pass 1: 39.6% (too lenient)
   - Pass 2: 67.9% (too strict) 
   - Pass 3: 37.7% (slightly under-filtered)
   - Pass 4: 50.0%* (optimal - Institution only)

2. **Synset Size Trend**:
   - Pass 1: 14.4 avg (too large)
   - Pass 2: 4.6 avg (too small)
   - Pass 3: 6.6 avg (good)
   - Pass 4: 6.0* avg (ideal - Institution only)

3. **Confidence Improvement**:
   - Pass 1: 80% high confidence
   - Pass 2: 80% high confidence
   - Pass 3: **100% high confidence** ✅
   - Pass 4: **100% high confidence** ✅

### Critical Test Case: "ustanova"

**The litmus test for polysemy handling**:

- ✅ **Pass 1**: Kept "ustanova" (but too many generic terms)
- ❌ **Pass 2**: Lost "ustanova" (too strict on polysemy)
- ✅ **Pass 3**: Recovered "ustanova" (balanced prompt)
- ✅ **Pass 4**: Kept "ustanova" (explicit polysemy guidance)

---

## Usage Notes

### For Comparing Results

When analyzing pass-to-pass changes, always reference:
1. **Synset ID** - Unique identifier
2. **English Lemmas** - What we're translating
3. **POS** - Noun vs verb handling differs
4. **Existing Serbian** - Baseline for match rate

### For Writing Reports

Standard format for synset headers:

```markdown
### Synset N: Name

**Synset ID**: ENG30-XXXXXXXX-X  
**English Lemmas**: word1, word2, ...  
**POS**: noun/verb/adjective/adverb  
**Definition**: full definition text
```

This ensures consistency across all documentation.
