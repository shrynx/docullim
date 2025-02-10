import sqlite3
import os
import threading


class Cache:
    def __init__(self, cache_dir=".docullim", db_name="cache.sqlite"):
        self.cache_dir = os.path.join(os.getcwd(), cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.db_path = os.path.join(self.cache_dir, db_name)
        # Use a lock to ensure that only one thread accesses the database at a time.
        self._lock = threading.Lock()
        # Allow the connection to be used in different threads.
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        query = "CREATE TABLE IF NOT EXISTS docs (hash TEXT PRIMARY KEY, doc TEXT)"
        with self._lock:
            self.connection.execute(query)
            self.connection.commit()

    def get(self, key: str):
        with self._lock:
            cursor = self.connection.execute(
                "SELECT doc FROM docs WHERE hash=?", (key,)
            )
            row = cursor.fetchone()
        if row:
            return row[0]
        return None

    def set(self, key: str, value: str):
        with self._lock:
            self.connection.execute(
                "REPLACE INTO docs (hash, doc) VALUES (?, ?)", (key, value)
            )
            self.connection.commit()

    def close(self):
        with self._lock:
            self.connection.close()
