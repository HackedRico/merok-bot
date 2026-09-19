from __future__ import annotations

import pyarrow as pa
import pytest

from shared.embed import HashEmbedder
from shared.llm.fake import FakeLLM
from tools.explain import explain, match
from tools.listen import listen


@pytest.fixture(scope="module")
def templates(hour_table: pa.Table):
    return listen(hour_table, min_authors=5)


def test_exact_and_near_matches_find_the_join_date_template(templates, embedder: HashEmbedder) -> None:
    exact, s1 = match("Do you REMEMBER when you joined X? I do! https://t.co/x #MyXAnniv", templates, embedder)
    assert exact is not None and s1 == 1.0 and "remember when you joined" in exact.normalised
    near, s2 = match("do you remember when you joined x? i sure do!", templates, embedder)
    assert near is not None and near.normalised == exact.normalised and 0.55 <= s2 < 1.0


def test_unrelated_text_matches_nothing(templates, embedder: HashEmbedder) -> None:
    t, s = match("The Senate votes on the farm bill Tuesday afternoon.", templates, embedder)
    assert t is None and s < 0.55


def test_explain_hands_the_model_only_the_facts(templates, embedder: HashEmbedder) -> None:
    llm = FakeLLM(["It is X's anniversary card meme."])
    e = explain("Do you remember when you joined X? I do!", templates, llm, embedder)
    assert e.template is not None and e.gloss.startswith("It is")
    request = llm.calls[0][1][0].content
    assert str(e.template.authors) in request and "organic" in request
