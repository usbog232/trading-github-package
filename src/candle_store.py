import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / 'data' / 'market_cache' / 'candles.db'


def timeframe_to_ms(timeframe: str) -> int:
    return 15 * 60 * 1000 if timeframe == '15m' else 60 * 60 * 1000 if timeframe == '1h' else 0


class CandleStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS candles (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open_time INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (symbol, timeframe, open_time)
                )
                '''
            )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_candles_symbol_tf_time ON candles(symbol, timeframe, open_time DESC)'
            )

    @staticmethod
    def _normalize_candle(raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'open_time': int(raw.get('t') or raw.get('open_time') or 0),
            'o': float(raw.get('o') or raw.get('open') or 0),
            'h': float(raw.get('h') or raw.get('high') or 0),
            'l': float(raw.get('l') or raw.get('low') or 0),
            'c': float(raw.get('c') or raw.get('close') or 0),
            'v': float(raw.get('v') or raw.get('volume') or 0),
        }

    def upsert_candles(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]], keep: int = 200) -> None:
        now_ms = int(time.time() * 1000)
        rows = [self._normalize_candle(c) for c in candles]
        rows = [r for r in rows if r['open_time'] > 0]
        with self._connect() as conn:
            conn.executemany(
                '''
                INSERT INTO candles(symbol, timeframe, open_time, open, high, low, close, volume, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, timeframe, open_time) DO UPDATE SET
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume,
                    updated_at=excluded.updated_at
                ''',
                [
                    (symbol, timeframe, r['open_time'], r['o'], r['h'], r['l'], r['c'], r['v'], now_ms)
                    for r in rows
                ],
            )
            conn.execute(
                '''
                DELETE FROM candles
                WHERE symbol = ? AND timeframe = ?
                  AND open_time NOT IN (
                    SELECT open_time FROM candles
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY open_time DESC
                    LIMIT ?
                  )
                ''',
                (symbol, timeframe, symbol, timeframe, keep),
            )

    def get_latest_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT open_time, open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND timeframe = ?
                ORDER BY open_time DESC
                LIMIT ?
                ''',
                (symbol, timeframe, limit),
            ).fetchall()
        rows = list(reversed(rows))
        return [
            {'t': row[0], 'o': row[1], 'h': row[2], 'l': row[3], 'c': row[4], 'v': row[5]}
            for row in rows
        ]

    def count_candles(self, symbol: str, timeframe: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = ?',
                (symbol, timeframe),
            ).fetchone()
        return int(row[0] if row else 0)

    def get_latest_open_time(self, symbol: str, timeframe: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT MAX(open_time) FROM candles WHERE symbol = ? AND timeframe = ?',
                (symbol, timeframe),
            ).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def replace_candles(self, symbol: str, timeframe: str, candles: List[Dict[str, Any]], keep: int = 200) -> None:
        with self._connect() as conn:
            conn.execute('DELETE FROM candles WHERE symbol = ? AND timeframe = ?', (symbol, timeframe))
        self.upsert_candles(symbol, timeframe, candles, keep=keep)

    def is_cache_healthy(self, symbol: str, timeframe: str, now_ms: int, keep: int = 200) -> bool:
        candles = self.get_latest_candles(symbol, timeframe, limit=keep)
        if len(candles) < keep:
            return False
        interval_ms = timeframe_to_ms(timeframe)
        if interval_ms <= 0:
            return False
        for prev, curr in zip(candles, candles[1:]):
            if int(curr['t']) - int(prev['t']) != interval_ms:
                return False
        latest_open = int(candles[-1]['t'])
        stale_limit = interval_ms * 2
        if now_ms - latest_open > stale_limit:
            return False
        return True
