from __future__ import annotations

import uuid
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.services.site_content import BLOG_COLUMNS, VIDEO_CATALOG


TINY_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def assert_ok(response, label: str) -> dict:
    if response.status_code >= 400:
        raise AssertionError(f"{label} failed: {response.status_code} {response.text}")
    return response.json()


def main() -> None:
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:8]

    user_a = assert_ok(
        client.post(
            "/api/auth/register",
            json={"username": f"ia_{suffix}", "password": "123456"},
        ),
        "register A",
    )
    user_b = assert_ok(
        client.post(
            "/api/auth/register",
            json={"username": f"ib_{suffix}", "password": "123456"},
        ),
        "register B",
    )

    headers_a = {"Authorization": f"Bearer {user_a['token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['token']}"}

    assert_ok(client.get("/api/auth/me", headers=headers_a), "restore A token")
    assert_ok(client.post("/api/auth/logout", headers=headers_a), "logout A")
    login_a = assert_ok(
        client.post(
            "/api/auth/login",
            json={"username": f"ia_{suffix}", "password": "123456"},
        ),
        "login A after logout",
    )
    headers_a = {"Authorization": f"Bearer {login_a['token']}"}
    assert_ok(client.get("/api/auth/me", headers=headers_a), "restore A login token")

    blog_content = (
        "这是一篇关于垃圾分类、可回收垃圾、厨余垃圾和校园投放互动的测试文章。\n"
        "[[博客配图]]\n"
        "图片应该出现在正文中间，而不是只能作为外部附件。"
    )

    created = assert_ok(
        client.post(
            "/api/blog/posts",
            headers=headers_a,
            json={
                "title": "宿舍垃圾分类跨账号测试",
                "content": blog_content,
                "column": BLOG_COLUMNS[0],
                "image_data_url": TINY_PNG_DATA_URL,
            },
        ),
        "A publish blog with image",
    )
    post_id = created["posts"][0]["id"]
    created_post = next(post for post in created["posts"] if post["id"] == post_id)
    if "[[博客配图]]" not in created_post["content"] or not created_post["image_data_url"]:
        raise AssertionError("Blog inline image marker or image data was not saved")

    posts_for_b = assert_ok(client.get("/api/blog/posts", headers=headers_b), "B list blogs")
    if not any(post["id"] == post_id for post in posts_for_b["posts"]):
        raise AssertionError("B cannot see A's blog post")

    commented = assert_ok(
        client.post(
            f"/api/blog/posts/{post_id}/comments",
            headers=headers_b,
            json={"content": "好"},
        ),
        "B comment A blog",
    )
    updated_post = next(post for post in commented["posts"] if post["id"] == post_id)
    if not updated_post["comments"]:
        raise AssertionError("B's blog comment was not saved")

    liked = assert_ok(
        client.post(f"/api/blog/posts/{post_id}/like", headers=headers_b, json={}),
        "B like A blog",
    )
    liked_post = next(post for post in liked["posts"] if post["id"] == post_id)
    if user_b["user"]["id"] not in liked_post["liked_user_ids"]:
        raise AssertionError("B's blog like was not saved")

    video_id = VIDEO_CATALOG[0]["id"]
    video_bundle = assert_ok(
        client.post(
            f"/api/recommendations/videos/{video_id}/comments",
            headers=headers_b,
            json={"content": "好"},
        ),
        "B comment video",
    )
    video = next(item for item in video_bundle["videos"] if item["id"] == video_id)
    if video["comment_count"] < 1:
        raise AssertionError("Video comment count did not update")

    dashboard_b = assert_ok(client.get("/api/auth/dashboard", headers=headers_b), "B dashboard")
    if not dashboard_b["commented_videos"]:
        raise AssertionError("B dashboard does not include commented video")

    unauthorized = client.post(
        f"/api/blog/posts/{post_id}/comments",
        json={"content": "未登录垃圾分类评论"},
    )
    if unauthorized.status_code != 401:
        raise AssertionError("Unauthenticated blog comment should return 401")

    print("site interaction check passed")


if __name__ == "__main__":
    main()
