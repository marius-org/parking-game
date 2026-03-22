from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncpg
import os
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Park Like a Pro API")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://parking:parkingpass@postgres-service:5432/parkingdb"
)
pool = None

@app.on_event("startup")
async def startup():
    global pool
    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
            async with pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS scores (
                        id          SERIAL PRIMARY KEY,
                        player_name VARCHAR(50)  NOT NULL,
                        score       INTEGER      NOT NULL,
                        created_at  TIMESTAMPTZ  DEFAULT NOW()
                    )
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scores_score
                    ON scores (score DESC)
                """)
            logger.info("Database ready.")
            break
        except Exception as e:
            logger.warning(f"DB attempt {attempt+1}/10: {e}")
            await asyncio.sleep(3)

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

class ScoreIn(BaseModel):
    player_name: str
    score: int

class ScoreOut(BaseModel):
    id: int
    player_name: str
    score: int

@app.get("/health")
async def health():
    return {"status": "ok", "service": "parking-game"}

@app.get("/api/scores", response_model=list[ScoreOut])
async def get_scores(limit: int = 10):
    if not pool:
        raise HTTPException(503, "Database unavailable")
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (player_name) id, player_name, score
            FROM scores
            ORDER BY player_name, score DESC
            LIMIT $1
            """,
            min(limit * 2, 200)
        )
    # re-sort by score and take top N
    sorted_rows = sorted([dict(r) for r in rows], key=lambda x: x['score'], reverse=True)
    return sorted_rows[:limit]

@app.post("/api/scores", response_model=ScoreOut, status_code=201)
async def post_score(data: ScoreIn):
    if not pool:
        raise HTTPException(503, "Database unavailable")
    if data.score < 0 or data.score > 99999:
        raise HTTPException(400, "Invalid score")
    name = data.player_name.strip()[:50] or "Driver"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO scores (player_name, score) VALUES ($1, $2) RETURNING id, player_name, score",
            name, data.score
        )
    return dict(row)

# Serve frontend
app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
