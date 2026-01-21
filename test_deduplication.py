"""Quick test for the deduplication helper function."""

from src.wordnet_autotranslate.pipelines.langgraph_translation_pipeline import LangGraphTranslationPipeline

# Initialize pipeline (we just need access to the helper method)
pipeline = LangGraphTranslationPipeline(
    source_lang="en",
    target_lang="sr",
    model="gpt-oss:120b"
)

print("=" * 70)
print("DEDUPLICATION HELPER TESTS")
print("=" * 70)

# Test Case 1: Verb compounds
test1 = ["metati", "pometati", "metati pod"]
result1 = pipeline._deduplicate_compounds(test1)
print(f"\n1️⃣ Verb compounds:")
print(f"   Input:  {test1}")
print(f"   Output: {result1}")
print(f"   ✅ Expected: ['metati', 'pometati'] (removed 'metati pod')")

# Test Case 2: Noun compounds
test2 = ["centar", "administrativni centar"]
result2 = pipeline._deduplicate_compounds(test2)
print(f"\n2️⃣ Noun compounds:")
print(f"   Input:  {test2}")
print(f"   Output: {result2}")
print(f"   ✅ Expected: ['centar'] (removed 'administrativni centar')")

# Test Case 3: Multiple compound detection
test3 = ["glavno sedište", "sedište"]
result3 = pipeline._deduplicate_compounds(test3)
print(f"\n3️⃣ Modifier detection:")
print(f"   Input:  {test3}")
print(f"   Output: {result3}")
print(f"   ✅ Expected: ['sedište'] (removed 'glavno sedište' - starts with 'glavn')")

# Test Case 4: No shared base - keep both
test4 = ["institucija", "ustanova"]
result4 = pipeline._deduplicate_compounds(test4)
print(f"\n4️⃣ No shared base:")
print(f"   Input:  {test4}")
print(f"   Output: {result4}")
print(f"   ✅ Expected: ['institucija', 'ustanova'] (unchanged)")

# Test Case 5: Mixed scenario
test5 = ["institucija", "ustanova", "javna ustanova", "centar", "upravni centar", "sedište", "glavno sedište"]
result5 = pipeline._deduplicate_compounds(test5)
print(f"\n5️⃣ Complex mixed scenario:")
print(f"   Input:  {test5}")
print(f"   Output: {result5}")
print(f"   ✅ Expected: ['institucija', 'ustanova', 'centar', 'sedište']")

# Test Case 6: All multiword expressions
test6 = ["metati pod", "baciti pod"]
result6 = pipeline._deduplicate_compounds(test6)
print(f"\n6️⃣ All multiword:")
print(f"   Input:  {test6}")
print(f"   Output: {result6}")
print(f"   ✅ Expected: ['metati pod', 'baciti pod'] (kept - no single-word bases)")

# Test Case 7: Comparative/superlative removal
test7 = ["najbolja institucija", "institucija", "najefikasniji centar", "centar"]
result7 = pipeline._deduplicate_compounds(test7)
print(f"\n7️⃣ Superlative detection (naj- prefix):")
print(f"   Input:  {test7}")
print(f"   Output: {result7}")
print(f"   ✅ Expected: ['institucija', 'centar'] (removed naj- forms)")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETE")
print("=" * 70)
