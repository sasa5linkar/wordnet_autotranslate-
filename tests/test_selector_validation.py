import pytest

from wordnet_autotranslate.workflows.selector_validation import (
    validate_selector_families,
)


def test_validate_selector_families_accepts_english_id():
    result = validate_selector_families(english_id="ENG30-00001740-n")
    assert result.selector_count == 1
    assert result.has_english_id


def test_validate_selector_families_rejects_conflicts():
    with pytest.raises(ValueError, match="exactly one selector"):
        validate_selector_families(
            english_id="ENG30-00001740-n",
            synset_name="entity.n.01",
        )
