from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import settings
from app.services.site_content import (
    BLOG_COLUMNS,
    RECOMMENDATION_TOPICS,
    SEED_BLOG_POSTS,
    VIDEO_CATALOG,
    build_recommendations,
    contains_theme_keyword,
    default_profile,
    sanitize_topics,
)


SYSTEM_USER_ID = "system-garbage-station"
SESSION_TTL_DAYS = 30
VIDEO_LOOKUP = {video["id"]: video for video in VIDEO_CATALOG}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def dumps_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads_json(raw: str | None, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex(), digest.hex()


def sanitize_display_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    if all(char in {"?", "？", "�"} for char in text):
        return ""
    return text


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


class SiteStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
        self._seed_system_content()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _init_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE COLLATE NOCASE NOT NULL,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS recommendation_profiles (
                    user_id TEXT PRIMARY KEY,
                    preferred_topics TEXT NOT NULL,
                    liked_video_ids TEXT NOT NULL,
                    favorite_video_ids TEXT NOT NULL,
                    viewed_video_ids TEXT NOT NULL,
                    detection_history TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS blog_posts (
                    id TEXT PRIMARY KEY,
                    author_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    image_data_url TEXT NOT NULL,
                    liked_user_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS blog_comments (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(post_id) REFERENCES blog_posts(id) ON DELETE CASCADE,
                    FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS video_comments (
                    id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            _ensure_column(connection, "users", "avatar_url", "TEXT NOT NULL DEFAULT ''")
            _ensure_column(connection, "users", "region", "TEXT NOT NULL DEFAULT ''")

    def _seed_system_content(self) -> None:
        with self._lock:
            with self._connect() as connection:
                system_exists = connection.execute(
                    "SELECT 1 FROM users WHERE id = ?",
                    (SYSTEM_USER_ID,),
                ).fetchone()
                if not system_exists:
                    salt, password_hash = hash_password("system-seed-only")
                    connection.execute(
                        """
                        INSERT INTO users (id, username, password_salt, password_hash, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (SYSTEM_USER_ID, "垃圾分类小站", salt, password_hash, utc_now()),
                    )

                post_count = connection.execute("SELECT COUNT(*) AS count FROM blog_posts").fetchone()["count"]
                if post_count:
                    return

                now = utc_now()
                for index, post in enumerate(SEED_BLOG_POSTS, start=1):
                    post_id = f"seed-post-{index}"
                    connection.execute(
                        """
                        INSERT INTO blog_posts (
                            id, author_id, title, content, column_name, image_data_url,
                            liked_user_ids, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            post_id,
                            SYSTEM_USER_ID,
                            post["title"],
                            post["content"],
                            post["column"],
                            "",
                            dumps_json([]),
                            now,
                            now,
                        ),
                    )

    def _serialize_user(self, row: sqlite3.Row) -> dict[str, str]:
        return {
            "id": row["id"],
            "username": row["username"],
            "created_at": row["created_at"],
            "avatar_url": row["avatar_url"] or "",
            "region": sanitize_display_text(row["region"]),
        }

    def _load_profile(self, connection: sqlite3.Connection, user_id: str) -> dict[str, list[str]]:
        row = connection.execute(
            """
            SELECT preferred_topics, liked_video_ids, favorite_video_ids, viewed_video_ids, detection_history
            FROM recommendation_profiles
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if not row:
            profile = default_profile()
            connection.execute(
                """
                INSERT INTO recommendation_profiles (
                    user_id, preferred_topics, liked_video_ids, favorite_video_ids,
                    viewed_video_ids, detection_history, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    dumps_json(profile["preferred_topics"]),
                    dumps_json(profile["liked_video_ids"]),
                    dumps_json(profile["favorite_video_ids"]),
                    dumps_json(profile["viewed_video_ids"]),
                    dumps_json(profile["detection_history"]),
                    utc_now(),
                ),
            )
            return profile

        return {
            "preferred_topics": sanitize_topics(loads_json(row["preferred_topics"], [])),
            "liked_video_ids": list(dict.fromkeys(loads_json(row["liked_video_ids"], [])))[:30],
            "favorite_video_ids": list(dict.fromkeys(loads_json(row["favorite_video_ids"], [])))[:30],
            "viewed_video_ids": list(dict.fromkeys(loads_json(row["viewed_video_ids"], [])))[:30],
            "detection_history": list(dict.fromkeys(loads_json(row["detection_history"], [])))[:8],
        }

    def _save_profile(self, connection: sqlite3.Connection, user_id: str, profile: dict[str, list[str]]) -> dict[str, list[str]]:
        normalized = {
            "preferred_topics": sanitize_topics(profile.get("preferred_topics")),
            "liked_video_ids": list(dict.fromkeys(profile.get("liked_video_ids", [])))[:30],
            "favorite_video_ids": list(dict.fromkeys(profile.get("favorite_video_ids", [])))[:30],
            "viewed_video_ids": list(dict.fromkeys(profile.get("viewed_video_ids", [])))[:30],
            "detection_history": list(dict.fromkeys(profile.get("detection_history", [])))[:8],
        }
        connection.execute(
            """
            INSERT INTO recommendation_profiles (
                user_id, preferred_topics, liked_video_ids, favorite_video_ids,
                viewed_video_ids, detection_history, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                preferred_topics = excluded.preferred_topics,
                liked_video_ids = excluded.liked_video_ids,
                favorite_video_ids = excluded.favorite_video_ids,
                viewed_video_ids = excluded.viewed_video_ids,
                detection_history = excluded.detection_history,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                dumps_json(normalized["preferred_topics"]),
                dumps_json(normalized["liked_video_ids"]),
                dumps_json(normalized["favorite_video_ids"]),
                dumps_json(normalized["viewed_video_ids"]),
                dumps_json(normalized["detection_history"]),
                utc_now(),
            ),
        )
        return normalized

    def _serialize_video_card(self, video: dict) -> dict:
        return {
            "id": video["id"],
            "title": video["title"],
            "description": video["description"],
            "platform": video["platform"],
            "source": video["source"],
            "duration": video["duration"],
            "url": video["url"],
            "cover_image": video.get("cover_image", ""),
            "topics": list(video.get("topics", [])),
            "focus_categories": list(video.get("focus_categories", [])),
        }

    def _load_video_stats(self, connection: sqlite3.Connection) -> dict[str, dict[str, int]]:
        stats = {
            video["id"]: {"like_count": 0, "favorite_count": 0, "comment_count": 0}
            for video in VIDEO_CATALOG
        }
        rows = connection.execute(
            "SELECT liked_video_ids, favorite_video_ids FROM recommendation_profiles"
        ).fetchall()
        for row in rows:
            for video_id in loads_json(row["liked_video_ids"], []):
                if video_id in stats:
                    stats[video_id]["like_count"] += 1
            for video_id in loads_json(row["favorite_video_ids"], []):
                if video_id in stats:
                    stats[video_id]["favorite_count"] += 1

        comment_rows = connection.execute(
            "SELECT video_id, content FROM video_comments"
        ).fetchall()
        for row in comment_rows:
            if row["video_id"] in stats and sanitize_display_text(row["content"]):
                stats[row["video_id"]]["comment_count"] += 1
        return stats

    def _load_video_comments(self, connection: sqlite3.Connection, video_ids: list[str]) -> dict[str, list[dict]]:
        if not video_ids:
            return {}

        placeholders = ", ".join("?" for _ in video_ids)
        rows = connection.execute(
            f"""
            SELECT
                comments.id,
                comments.video_id,
                comments.author_id,
                users.username AS author_name,
                users.avatar_url AS author_avatar_url,
                users.region AS author_region,
                comments.content,
                comments.created_at
            FROM video_comments AS comments
            JOIN users ON users.id = comments.author_id
            WHERE comments.video_id IN ({placeholders})
            ORDER BY comments.created_at DESC
            """,
            tuple(video_ids),
        ).fetchall()

        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            content = sanitize_display_text(row["content"])
            if not content:
                continue
            grouped[row["video_id"]].append(
                {
                    "id": row["id"],
                    "author_id": row["author_id"],
                    "author_name": row["author_name"],
                    "author_avatar_url": row["author_avatar_url"] or "",
                    "author_region": sanitize_display_text(row["author_region"]),
                    "content": content,
                    "created_at": row["created_at"],
                }
            )
        return grouped

    def _create_session(self, connection: sqlite3.Connection, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(days=SESSION_TTL_DAYS)
        connection.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, created_at.isoformat(), expires_at.isoformat()),
        )
        return token

    def _user_snapshot(self, connection: sqlite3.Connection, user_id: str) -> tuple[dict, dict]:
        row = connection.execute(
            "SELECT id, username, created_at, avatar_url, region FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise ValueError("当前账号不存在。")
        profile = self._load_profile(connection, user_id)
        return self._serialize_user(row), profile

    def register_user(self, username: str, password: str) -> tuple[dict, dict, str]:
        safe_username = username.strip()
        if len(safe_username) < 2 or len(safe_username) > 20:
            raise ValueError("用户名长度需要在 2 到 20 个字符之间。")
        if any(char.isspace() for char in safe_username):
            raise ValueError("用户名不能包含空格。")
        if len(password) < 6:
            raise ValueError("密码至少需要 6 位。")

        with self._lock:
            with self._connect() as connection:
                exists = connection.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    (safe_username,),
                ).fetchone()
                if exists:
                    raise ValueError("这个用户名已经被注册了。")

                user_id = str(uuid.uuid4())
                salt, password_hash = hash_password(password)
                created_at = utc_now()
                connection.execute(
                    """
                    INSERT INTO users (id, username, password_salt, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, safe_username, salt, password_hash, created_at),
                )
                profile = self._load_profile(connection, user_id)
                token = self._create_session(connection, user_id)
                user, profile = self._user_snapshot(connection, user_id)
                return user, profile, token

    def login_user(self, username: str, password: str) -> tuple[dict, dict, str]:
        safe_username = username.strip()
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT id, username, password_salt, password_hash, created_at
                    FROM users
                    WHERE username = ?
                    """,
                    (safe_username,),
                ).fetchone()
                if not row:
                    raise ValueError("用户名或密码不正确。")

                _, password_hash = hash_password(password, row["password_salt"])
                if not hmac.compare_digest(password_hash, row["password_hash"]):
                    raise ValueError("用户名或密码不正确。")

                token = self._create_session(connection, row["id"])
                user, profile = self._user_snapshot(connection, row["id"])
                return user, profile, token

    def logout(self, token: str) -> None:
        if not token:
            return
        with self._lock:
            with self._connect() as connection:
                connection.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def get_user_by_token(self, token: str | None) -> dict | None:
        if not token:
            return None

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    sessions.user_id,
                    sessions.expires_at,
                    users.id,
                    users.username,
                    users.created_at,
                    users.avatar_url,
                    users.region
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
            if not row:
                return None

            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(UTC):
                connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None

            return {
                "id": row["id"],
                "username": row["username"],
                "created_at": row["created_at"],
                "avatar_url": row["avatar_url"] or "",
                "region": row["region"] or "",
                "token": token,
            }

    def get_user_state(self, user_id: str) -> tuple[dict, dict]:
        with self._connect() as connection:
            return self._user_snapshot(connection, user_id)

    def update_user_profile(self, user_id: str, avatar_data_url: str, region: str) -> tuple[dict, dict]:
        safe_region = region.strip()[:30]
        safe_avatar = avatar_data_url.strip()
        if safe_avatar and not safe_avatar.startswith("data:image/"):
            raise ValueError("头像格式不正确，请重新上传图片。")

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE users SET avatar_url = ?, region = ? WHERE id = ?",
                    (safe_avatar, safe_region, user_id),
                )
                return self._user_snapshot(connection, user_id)

    def get_user_dashboard(self, user_id: str) -> dict:
        with self._connect() as connection:
            user, profile = self._user_snapshot(connection, user_id)
            liked_videos = [
                self._serialize_video_card(VIDEO_LOOKUP[video_id])
                for video_id in profile["liked_video_ids"]
                if video_id in VIDEO_LOOKUP
            ]

            comment_rows = connection.execute(
                """
                SELECT id, video_id, content, created_at
                FROM video_comments
                WHERE author_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            commented_videos = [
                {
                    "comment_id": row["id"],
                    "video": self._serialize_video_card(VIDEO_LOOKUP[row["video_id"]]),
                    "content": sanitize_display_text(row["content"]),
                    "created_at": row["created_at"],
                }
                for row in comment_rows
                if row["video_id"] in VIDEO_LOOKUP and sanitize_display_text(row["content"])
            ]

        published_posts = [
            post
            for post in self.list_blog_posts()["posts"]
            if post["author_id"] == user_id
        ]
        return {
            "user": user,
            "profile": profile,
            "liked_videos": liked_videos,
            "commented_videos": commented_videos,
            "published_posts": published_posts,
        }

    def get_recommendation_bundle(self, user_id: str | None) -> dict:
        profile = default_profile()
        comment_lookup: dict[str, list[dict]] = {}
        stats_lookup = {
            video["id"]: {"like_count": 0, "favorite_count": 0, "comment_count": 0}
            for video in VIDEO_CATALOG
        }
        if user_id:
            with self._connect() as connection:
                profile = self._load_profile(connection, user_id)
                comment_lookup = self._load_video_comments(connection, [video["id"] for video in VIDEO_CATALOG])
                stats_lookup = self._load_video_stats(connection)
        else:
            with self._connect() as connection:
                comment_lookup = self._load_video_comments(connection, [video["id"] for video in VIDEO_CATALOG])
                stats_lookup = self._load_video_stats(connection)

        videos = build_recommendations(profile)
        liked_ids = set(profile["liked_video_ids"])
        favorite_ids = set(profile["favorite_video_ids"])
        viewed_ids = set(profile["viewed_video_ids"])
        for video in videos:
            video["comments"] = comment_lookup.get(video["id"], [])[:6]
            video["liked"] = video["id"] in liked_ids
            video["favorited"] = video["id"] in favorite_ids
            video["viewed"] = video["id"] in viewed_ids
            video["like_count"] = stats_lookup.get(video["id"], {}).get("like_count", 0)
            video["favorite_count"] = stats_lookup.get(video["id"], {}).get("favorite_count", 0)
            video["comment_count"] = stats_lookup.get(video["id"], {}).get("comment_count", 0)

        return {
            "topics": RECOMMENDATION_TOPICS,
            "videos": videos,
            "profile": profile,
        }

    def update_preferences(self, user_id: str, preferred_topics: list[str]) -> dict:
        with self._lock:
            with self._connect() as connection:
                profile = self._load_profile(connection, user_id)
                profile["preferred_topics"] = sanitize_topics(preferred_topics)
                self._save_profile(connection, user_id, profile)
        return self.get_recommendation_bundle(user_id)

    def record_video_action(self, user_id: str, video_id: str, action: str) -> dict:
        valid_video_ids = {video["id"] for video in VIDEO_CATALOG}
        if video_id not in valid_video_ids:
            raise ValueError("未找到对应的推荐视频。")
        if action not in {"view", "like", "favorite"}:
            raise ValueError("不支持的推荐动作。")

        with self._lock:
            with self._connect() as connection:
                profile = self._load_profile(connection, user_id)

                if action == "view":
                    viewed = [item for item in profile["viewed_video_ids"] if item != video_id]
                    viewed.insert(0, video_id)
                    profile["viewed_video_ids"] = viewed[:30]
                elif action == "like":
                    liked = set(profile["liked_video_ids"])
                    if video_id in liked:
                        liked.remove(video_id)
                    else:
                        liked.add(video_id)
                    profile["liked_video_ids"] = list(liked)
                elif action == "favorite":
                    favorites = set(profile["favorite_video_ids"])
                    if video_id in favorites:
                        favorites.remove(video_id)
                    else:
                        favorites.add(video_id)
                    profile["favorite_video_ids"] = list(favorites)

                self._save_profile(connection, user_id, profile)

        return self.get_recommendation_bundle(user_id)

    def add_video_comment(self, user_id: str, video_id: str, content: str) -> dict:
        safe_content = content.strip()
        if video_id not in VIDEO_LOOKUP:
            raise ValueError("要评论的视频不存在。")
        if len(safe_content) < 2:
            raise ValueError("评论至少需要 2 个字。")
        if len(safe_content) > 160:
            raise ValueError("评论请控制在 160 个字以内。")

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO video_comments (id, video_id, author_id, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), video_id, user_id, safe_content, utc_now()),
                )

        return self.get_recommendation_bundle(user_id)

    def record_detection(self, user_id: str, waste_category: str) -> None:
        if waste_category not in {"可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾"}:
            return
        with self._lock:
            with self._connect() as connection:
                profile = self._load_profile(connection, user_id)
                history = [item for item in profile["detection_history"] if item != waste_category]
                history.insert(0, waste_category)
                profile["detection_history"] = history[:8]
                self._save_profile(connection, user_id, profile)

    def list_blog_posts(self) -> dict:
        with self._connect() as connection:
            posts = connection.execute(
                """
                SELECT
                    posts.id,
                    posts.author_id,
                    users.username AS author_name,
                    posts.title,
                    posts.content,
                    posts.column_name,
                    posts.image_data_url,
                    posts.liked_user_ids,
                    posts.created_at,
                    posts.updated_at
                FROM blog_posts AS posts
                JOIN users ON users.id = posts.author_id
                ORDER BY posts.created_at DESC
                """
            ).fetchall()

            serialized_posts = []
            for row in posts:
                comments_rows = connection.execute(
                    """
                    SELECT comments.id, comments.author_id, users.username AS author_name, comments.content, comments.created_at
                    FROM blog_comments AS comments
                    JOIN users ON users.id = comments.author_id
                    WHERE comments.post_id = ?
                    ORDER BY comments.created_at ASC
                    """,
                    (row["id"],),
                ).fetchall()
                serialized_posts.append(
                    {
                        "id": row["id"],
                        "author_id": row["author_id"],
                        "author_name": row["author_name"],
                        "title": row["title"],
                        "content": row["content"],
                        "column": row["column_name"],
                        "image_data_url": row["image_data_url"] or "",
                        "liked_user_ids": loads_json(row["liked_user_ids"], []),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "comments": [
                            {
                                "id": comment["id"],
                                "author_id": comment["author_id"],
                                "author_name": comment["author_name"],
                                "content": comment["content"],
                                "created_at": comment["created_at"],
                            }
                            for comment in comments_rows
                        ],
                    }
                )

        return {
            "columns": BLOG_COLUMNS,
            "posts": serialized_posts,
        }

    def create_blog_post(self, user_id: str, title: str, content: str, column: str, image_data_url: str = "") -> dict:
        safe_title = title.strip()
        safe_content = content.strip()
        if len(safe_title) < 4:
            raise ValueError("标题至少需要 4 个字。")
        if len(safe_content) < 20:
            raise ValueError("博客内容至少需要 20 个字。")
        if column not in BLOG_COLUMNS:
            raise ValueError("博客栏目不在允许范围内。")
        if not contains_theme_keyword(f"{safe_title}\n{safe_content}"):
            raise ValueError("博客内容必须围绕垃圾分类、回收、厨余或有害垃圾主题。")
        if image_data_url and not image_data_url.startswith("data:image/"):
            raise ValueError("博客图片格式不正确。")

        with self._lock:
            with self._connect() as connection:
                post_id = str(uuid.uuid4())
                now = utc_now()
                connection.execute(
                    """
                    INSERT INTO blog_posts (
                        id, author_id, title, content, column_name, image_data_url,
                        liked_user_ids, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_id,
                        user_id,
                        safe_title,
                        safe_content,
                        column,
                        image_data_url or "",
                        dumps_json([]),
                        now,
                        now,
                    ),
                )

        return self.list_blog_posts()

    def toggle_blog_like(self, user_id: str, post_id: str) -> dict:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT liked_user_ids FROM blog_posts WHERE id = ?",
                    (post_id,),
                ).fetchone()
                if not row:
                    raise ValueError("要点赞的博客不存在。")

                liked = set(loads_json(row["liked_user_ids"], []))
                if user_id in liked:
                    liked.remove(user_id)
                else:
                    liked.add(user_id)
                connection.execute(
                    "UPDATE blog_posts SET liked_user_ids = ?, updated_at = ? WHERE id = ?",
                    (dumps_json(list(liked)), utc_now(), post_id),
                )

        return self.list_blog_posts()

    def add_blog_comment(self, user_id: str, post_id: str, content: str) -> dict:
        safe_content = content.strip()
        if len(safe_content) < 6:
            raise ValueError("评论至少需要 6 个字。")
        if not contains_theme_keyword(safe_content):
            raise ValueError("评论内容也需要围绕垃圾分类主题展开。")

        with self._lock:
            with self._connect() as connection:
                exists = connection.execute("SELECT 1 FROM blog_posts WHERE id = ?", (post_id,)).fetchone()
                if not exists:
                    raise ValueError("要评论的博客不存在。")
                connection.execute(
                    """
                    INSERT INTO blog_comments (id, post_id, author_id, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), post_id, user_id, safe_content, utc_now()),
                )

        return self.list_blog_posts()

    def delete_blog_post(self, user_id: str, post_id: str) -> dict:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT author_id FROM blog_posts WHERE id = ?",
                    (post_id,),
                ).fetchone()
                if not row:
                    raise ValueError("要删除的博客不存在。")
                if row["author_id"] != user_id:
                    raise ValueError("只能删除自己发布的博客。")
                connection.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))

        return self.list_blog_posts()


site_store = SiteStore(settings.artifact_dir / "data" / "ecosort_site.db")
