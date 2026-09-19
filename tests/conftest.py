from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from shared.config import Settings, load_settings
from shared.data.fixture import FixtureSource
from shared.embed import HashEmbedder
from shared.llm.fake import FakeLLM

# =============================================================================
# Module Overview
# =============================================================================
# The local adapters every test runs on: the fixture data source, the hashing
# embedder, and a fake model. Session-scoped tables are read once.

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def settings() -> Settings:
    # Tests run on the test adapters by name; the app's defaults are the real ones.
    return load_settings(env={"MEROK_DATA_SOURCE": "fixture", "MEROK_PUBLISHER": "dry_run", "MEROK_POLLER": "replay"}, repo_root=ROOT)


@pytest.fixture(scope="session")
def source(settings: Settings) -> FixtureSource:
    return FixtureSource(settings.fixtures_dir)


@pytest.fixture(scope="session")
def hour_table(source: FixtureSource) -> pa.Table:
    return source.firehose()


@pytest.fixture(scope="session")
def gov_table(source: FixtureSource) -> pa.Table:
    return source.gov_tweets()


@pytest.fixture(scope="session")
def embedder() -> HashEmbedder:
    return HashEmbedder()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM(["reply one", "reply two"])
