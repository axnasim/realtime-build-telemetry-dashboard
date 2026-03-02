import aiosqlite
from typing import List, Dict
from src.models import BuildMetric

class MetricsStorage:
    def __init__(self, db_path: str = "data/metrics.db"):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS build_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    build_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_build_id ON build_metrics (build_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON build_metrics (agent_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON build_metrics (timestamp)")
            await db.commit()

    async def insert_metric(self, metric: BuildMetric):
        """Insert a build metric"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO build_metrics (agent_id, build_id, status, duration_ms) VALUES (?, ?, ?, ?)",
                (metric.agent_id, metric.build_id, metric.status, metric.duration_ms)
            )
            await db.commit()

    async def check_flaky_build(self, build_id: str) -> bool:
        """Check if a build has inconsistent results (flaky)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT status FROM build_metrics WHERE build_id = ?",
                (build_id,)
            )
            statuses = await cursor.fetchall()
            # If we have both PASS and FAIL for the same build_id, it's flaky
            return len(statuses) > 1

    async def get_summary(self) -> Dict:
        """Get aggregated statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            # Total counts
            cursor = await db.execute(
                "SELECT status, COUNT(*) as count FROM build_metrics GROUP BY status"
            )
            status_counts = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # Average duration
            cursor = await db.execute(
                "SELECT AVG(duration_ms) as avg_duration FROM build_metrics"
            )
            avg_duration = (await cursor.fetchone())[0] or 0
            
            # Flaky builds
            cursor = await db.execute("""
                SELECT build_id, COUNT(DISTINCT status) as status_count
                FROM build_metrics
                GROUP BY build_id
                HAVING status_count > 1
            """)
            flaky_builds = [row[0] for row in await cursor.fetchall()]
            
            # Recent failures
            cursor = await db.execute("""
                SELECT build_id, agent_id, duration_ms, timestamp
                FROM build_metrics
                WHERE status = 'FAIL'
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            recent_failures = [
                {
                    "build_id": row[0],
                    "agent_id": row[1],
                    "duration_ms": row[2],
                    "timestamp": row[3]
                }
                for row in await cursor.fetchall()
            ]
            
            return {
                "status_counts": status_counts,
                "avg_duration_ms": avg_duration,
                "flaky_builds": flaky_builds,
                "flaky_count": len(flaky_builds),
                "recent_failures": recent_failures
            }

    async def get_build_history(self, build_id: str) -> List[Dict]:
        """Get all runs for a specific build"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT agent_id, status, duration_ms, timestamp FROM build_metrics WHERE build_id = ? ORDER BY timestamp",
                (build_id,)
            )
            return [
                {
                    "agent_id": row[0],
                    "status": row[1],
                    "duration_ms": row[2],
                    "timestamp": row[3]
                }
                for row in await cursor.fetchall()
            ]