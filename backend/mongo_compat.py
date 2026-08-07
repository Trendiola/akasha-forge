"""AF-DESKTOP-004 — Async, motor-compatible shim over montydb (local desktop DB).

Only the subset of the motor/pymongo API actually used by Akasha Forge is
implemented (audited surface): find/find_one (+projection), chainable cursor
(sort/skip/limit/to_list + async iteration), insert_one/insert_many,
update_one/update_many ($set/$setOnInsert/upsert), delete_one/delete_many,
count_documents, distinct, create_index. montydb runs synchronously, so calls
are dispatched to a single worker thread to preserve async semantics and avoid
concurrency issues. Persistence uses montydb's SQLite backend under
<AKASHA_DATA_DIR>/database/.
"""
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Single worker → serialize montydb access (safe for a single-user desktop app).
_EXECUTOR = ThreadPoolExecutor(max_workers=1)

# montydb's sqlite backend raises these on a collection whose backing store was
# never created (no document ever inserted): either the per-collection db file
# is missing ("unable to open database file") or its table was never created
# ("no such table: documents"). Real MongoDB treats reads/deletes on such a
# namespace as a no-op, so we mirror that — and ONLY for these specific cases,
# re-raising every other OperationalError untouched.
_MISSING_COLLECTION_MSGS = ("unable to open database file", "no such table")


def _is_missing_collection(exc: Exception) -> bool:
    return isinstance(exc, sqlite3.OperationalError) and any(
        msg in str(exc) for msg in _MISSING_COLLECTION_MSGS
    )


class _DeleteResult:
    """Minimal pymongo-compatible result for a no-op delete."""

    def __init__(self):
        self.deleted_count = 0
        self.acknowledged = True
        self.raw_result = {"n": 0, "ok": 1.0}


def _guard(fn, default):
    """Run fn; if montydb hits a not-yet-created collection, return default."""
    try:
        return fn()
    except sqlite3.OperationalError as exc:
        if _is_missing_collection(exc):
            return default() if callable(default) else default
        raise


async def _run(fn):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_EXECUTOR, fn)


class _Cursor:
    def __init__(self, coll, flt, projection):
        self._coll = coll
        self._filter = flt
        self._projection = projection
        self._sort = None
        self._skip = 0
        self._limit = 0

    def sort(self, *args):
        self._sort = args
        return self

    def skip(self, n):
        self._skip = int(n or 0)
        return self

    def limit(self, n):
        self._limit = int(n or 0)
        return self

    def _materialize(self):
        def _do():
            cur = self._coll.find(self._filter, self._projection)
            if self._sort is not None:
                cur = cur.sort(*self._sort)
            if self._skip:
                cur = cur.skip(self._skip)
            if self._limit:
                cur = cur.limit(self._limit)
            return list(cur)
        return _guard(_do, list)

    async def to_list(self, length=None):
        return await _run(self._materialize)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for doc in await _run(self._materialize):
            yield doc


class _Collection:
    def __init__(self, coll):
        self._c = coll

    async def find_one(self, flt=None, projection=None, sort=None, **kwargs):
        def _fn():
            if sort is not None:
                cur = self._c.find(flt or {}, projection).sort(sort).limit(1)
                for doc in cur:
                    return doc
                return None
            return self._c.find_one(flt or {}, projection)
        return await _run(lambda: _guard(_fn, None))

    def find(self, flt=None, projection=None):
        return _Cursor(self._c, flt or {}, projection)

    async def insert_one(self, doc):
        return await _run(lambda: self._c.insert_one(doc))

    async def insert_many(self, docs):
        return await _run(lambda: self._c.insert_many(list(docs)))

    async def update_one(self, flt, update, upsert=False):
        return await _run(lambda: self._c.update_one(flt, update, upsert=upsert))

    async def update_many(self, flt, update, upsert=False):
        return await _run(lambda: self._c.update_many(flt, update, upsert=upsert))

    async def delete_one(self, flt):
        return await _run(lambda: _guard(lambda: self._c.delete_one(flt), _DeleteResult))

    async def delete_many(self, flt):
        return await _run(lambda: _guard(lambda: self._c.delete_many(flt), _DeleteResult))

    async def count_documents(self, flt=None):
        return await _run(lambda: _guard(lambda: self._c.count_documents(flt or {}), 0))

    async def distinct(self, key, flt=None):
        return await _run(lambda: _guard(lambda: self._c.distinct(key, flt or {}), list))

    async def create_index(self, keys, **kwargs):
        def _mk():
            try:
                # montydb doesn't support text-index weights/name kwargs; degrade gracefully.
                return self._c.create_index(keys, unique=kwargs.get("unique", False))
            except Exception:
                return None
        return await _run(_mk)


class _Database:
    def __init__(self, mdb):
        object.__setattr__(self, "_mdb", mdb)
        object.__setattr__(self, "_cache", {})

    def __getitem__(self, name):
        cache = object.__getattribute__(self, "_cache")
        if name not in cache:
            cache[name] = _Collection(object.__getattribute__(self, "_mdb")[name])
        return cache[name]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]


def make_local_db(data_dir, db_name: str):
    """Configure montydb (sqlite) under <data_dir>/database/ and return (client, db-shim)."""
    from montydb import set_storage, MontyClient

    db_path = Path(data_dir) / "database"
    db_path.mkdir(parents=True, exist_ok=True)
    set_storage(repository=str(db_path), storage="sqlite")
    client = MontyClient(str(db_path))
    return client, _Database(client[db_name])
