"""
Vox Database v3.0
SQLite — users, auth, auto-login, face, voice-print flag, logs, performance
"""
import sqlite3, hashlib, os, json
from datetime import datetime


class VoxDatabase:
    def __init__(self, db_path=None):
        if not db_path:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base, "data", "Vox.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.path = db_path
        self._init()
        print(f"✅ DB: {db_path}")

    def _conn(self):
        c = sqlite3.connect(self.path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                username       TEXT UNIQUE NOT NULL,
                password_hash  TEXT NOT NULL,
                full_name      TEXT DEFAULT '',
                email          TEXT DEFAULT '',
                face_data      TEXT,
                voice_enrolled INTEGER DEFAULT 0,
                auto_login     INTEGER DEFAULT 0,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login     TEXT
            );
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER DEFAULT 0,
                command     TEXT,
                intent      TEXT,
                response    TEXT,
                duration_ms INTEGER DEFAULT 0,
                timestamp   TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS search_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER DEFAULT 0,
                query     TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS web_results (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                title     TEXT,
                url       TEXT,
                position  INTEGER
            );
            CREATE TABLE IF NOT EXISTS performance_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event       TEXT,
                duration_ms INTEGER,
                timestamp   TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)

    # ── AUTH ──────────────────────────────────────
    @staticmethod
    def _h(pw): return hashlib.sha256(pw.encode()).hexdigest()

    def register(self, username, password, full_name="", email=""):
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO users(username,password_hash,full_name,email) VALUES(?,?,?,?)",
                    (username.lower(), self._h(password), full_name, email)
                )
            return True, f"Account created! Welcome, {full_name or username}!"
        except sqlite3.IntegrityError:
            return False, "Username already taken."
        except Exception as e:
            return False, str(e)

    def login(self, username, password):
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM users WHERE username=? AND password_hash=?",
                (username.lower(), self._h(password))
            ).fetchone()
            if row:
                c.execute("UPDATE users SET last_login=? WHERE id=?",
                          (datetime.now().isoformat(), row['id']))
                return True, dict(row)
        return False, {}

    def get_auto_login_user(self):
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM users WHERE auto_login=1 LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def set_auto_login(self, user_id, enabled: bool):
        with self._conn() as c:
            c.execute("UPDATE users SET auto_login=0")
            if enabled:
                c.execute("UPDATE users SET auto_login=1 WHERE id=?", (user_id,))

    def set_voice_enrolled(self, user_id, enrolled: bool):
        with self._conn() as c:
            c.execute("UPDATE users SET voice_enrolled=? WHERE id=?",
                      (1 if enrolled else 0, user_id))

    # ── FACE ──────────────────────────────────────
    def save_face(self, user_id, encoding):
        try:
            data = json.dumps(encoding.tolist() if hasattr(encoding, 'tolist') else list(encoding))
            with self._conn() as c:
                c.execute("UPDATE users SET face_data=? WHERE id=?", (data, user_id))
            return True
        except Exception:
            return False

    def get_all_faces(self):
        try:
            import numpy as np
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id,username,full_name,face_data FROM users WHERE face_data IS NOT NULL"
                ).fetchall()
            result = []
            for r in rows:
                enc = np.array(json.loads(r['face_data']))
                result.append({'user_id': r['id'], 'username': r['username'],
                               'full_name': r['full_name'], 'encoding': enc})
            return result
        except Exception:
            return []

    # ── LOGS ──────────────────────────────────────
    def log_command(self, command, intent, response, user_id=0, ms=0):
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO conversation_logs(user_id,command,intent,response,duration_ms) VALUES(?,?,?,?,?)",
                    (user_id, command, intent, response, ms)
                )
        except Exception:
            pass

    # keep old name for compatibility
    def add_log(self, command, intent, response, user_id=0, duration_ms=0):
        self.log_command(command, intent, response, user_id, duration_ms)

    def log_perf(self, event, ms):
        try:
            with self._conn() as c:
                c.execute("INSERT INTO performance_logs(event,duration_ms) VALUES(?,?)", (event, ms))
        except Exception:
            pass

    def save_search(self, user_id, query, results):
        try:
            with self._conn() as c:
                cur = c.execute(
                    "INSERT INTO search_history(user_id,query) VALUES(?,?)", (user_id, query)
                )
                sid = cur.lastrowid
                for i, r in enumerate(results):
                    c.execute(
                        "INSERT INTO web_results(search_id,title,url,position) VALUES(?,?,?,?)",
                        (sid, r.get('title',''), r.get('url',''), i+1)
                    )
                return sid
        except Exception:
            return 0

    def get_last_results(self, user_id):
        try:
            with self._conn() as c:
                sh = c.execute(
                    "SELECT id FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 1",
                    (user_id,)
                ).fetchone()
                if sh:
                    rows = c.execute(
                        "SELECT title,url,position FROM web_results WHERE search_id=? ORDER BY position",
                        (sh['id'],)
                    ).fetchall()
                    return [dict(r) for r in rows]
        except Exception:
            pass
        return []

    def get_history(self, user_id, limit=100):
        with self._conn() as c:
            rows = c.execute(
                "SELECT command,intent,response,duration_ms,timestamp FROM conversation_logs "
                "WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]


