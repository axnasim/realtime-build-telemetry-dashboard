import pytest
from src.storage import MetricsStorage
from src.models import BuildMetric


@pytest.fixture
async def storage(tmp_path):
    s = MetricsStorage(db_path=str(tmp_path / "test.db"))
    await s.init_db()
    return s


async def test_init_db_creates_table(tmp_path):
    s = MetricsStorage(db_path=str(tmp_path / "test.db"))
    await s.init_db()
    # init_db is idempotent; calling twice should not raise
    await s.init_db()


async def test_insert_and_summary(storage):
    metric = BuildMetric(agent_id="a1", build_id="b1", status="PASS", duration_ms=1000)
    await storage.insert_metric(metric)

    summary = await storage.get_summary()
    assert summary["status_counts"].get("PASS") == 1
    assert summary["avg_duration_ms"] == 1000
    assert summary["flaky_count"] == 0
    assert summary["recent_failures"] == []


async def test_summary_fail_appears_in_recent(storage):
    metric = BuildMetric(agent_id="a2", build_id="b-fail", status="FAIL", duration_ms=3000)
    await storage.insert_metric(metric)

    summary = await storage.get_summary()
    assert summary["status_counts"].get("FAIL") == 1
    assert len(summary["recent_failures"]) == 1
    assert summary["recent_failures"][0]["build_id"] == "b-fail"


async def test_flaky_detection(storage):
    m1 = BuildMetric(agent_id="a1", build_id="flaky", status="PASS", duration_ms=500)
    m2 = BuildMetric(agent_id="a2", build_id="flaky", status="FAIL", duration_ms=600)

    await storage.insert_metric(m1)
    assert not await storage.check_flaky_build("flaky")

    await storage.insert_metric(m2)
    assert await storage.check_flaky_build("flaky")

    summary = await storage.get_summary()
    assert summary["flaky_count"] == 1
    assert "flaky" in summary["flaky_builds"]


async def test_non_flaky_build(storage):
    m1 = BuildMetric(agent_id="a1", build_id="stable", status="PASS", duration_ms=100)
    m2 = BuildMetric(agent_id="a2", build_id="stable", status="PASS", duration_ms=200)
    await storage.insert_metric(m1)
    await storage.insert_metric(m2)
    assert not await storage.check_flaky_build("stable")


async def test_build_history(storage):
    m = BuildMetric(agent_id="a1", build_id="b-hist", status="PASS", duration_ms=2000)
    await storage.insert_metric(m)

    history = await storage.get_build_history("b-hist")
    assert len(history) == 1
    assert history[0]["status"] == "PASS"
    assert history[0]["agent_id"] == "a1"
    assert history[0]["duration_ms"] == 2000


async def test_build_history_empty(storage):
    history = await storage.get_build_history("nonexistent")
    assert history == []
