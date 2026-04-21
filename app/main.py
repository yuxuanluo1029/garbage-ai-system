from __future__ import annotations

import base64
import binascii
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AuthRequest,
    AuthResponse,
    BlogCommentCreateRequest,
    BlogPostCreateRequest,
    BlogResponse,
    MeResponse,
    PreferenceUpdateRequest,
    PredictionResponse,
    ProfileUpdateRequest,
    RecommendationCommentCreateRequest,
    RecommendationResponse,
    UserDashboardResponse,
    VideoActionRequest,
)
from app.services.agent import agent_service
from app.services.detector import get_detector, save_upload
from app.services.site_store import site_store


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=settings.app_title)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix) :].strip()
    return authorization.strip() or None


def _validate_blog_image(image_data_url: str) -> None:
    if not image_data_url:
        return
    if not image_data_url.startswith("data:image/") or "," not in image_data_url:
        raise HTTPException(status_code=400, detail="博客配图格式不正确。")

    _, encoded = image_data_url.split(",", 1)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="博客配图无法解析。") from exc

    suffix = ".png"
    target = save_upload(raw, suffix)
    detector = get_detector()
    prediction = detector.predict(target)
    if prediction.summary_category == "待确认":
        raise HTTPException(
            status_code=400,
            detail="博客配图需要与垃圾分类主题相关，请上传可识别的垃圾分类图片。",
        )


def get_optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    token = _extract_token(authorization)
    return site_store.get_user_by_token(token)


def get_required_user(current_user: dict | None = Depends(get_optional_user)) -> dict:
    if current_user is None:
        raise HTTPException(status_code=401, detail="请先登录后再进行这个操作。")
    return current_user


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/predict", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    current_user: dict | None = Depends(get_optional_user),
) -> PredictionResponse:
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空。")

    try:
        target = save_upload(content, suffix)
        detector = get_detector()
        prediction = detector.predict(target)
        if current_user is not None:
            site_store.record_detection(current_user["id"], prediction.summary_category)
        return prediction
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"识别失败：{exc}") from exc


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        answer, provider = agent_service.analyze(request)
        return AnalyzeResponse(answer=answer, provider=provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"分析失败：{exc}") from exc


@app.post("/api/auth/register", response_model=AuthResponse)
async def register(payload: AuthRequest) -> AuthResponse:
    try:
        user, profile, token = site_store.register_user(payload.username, payload.password)
        return AuthResponse(message="注册成功，已自动登录。", token=token, user=user, profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(payload: AuthRequest) -> AuthResponse:
    try:
        user, profile, token = site_store.login_user(payload.username, payload.password)
        return AuthResponse(message="登录成功。", token=token, user=user, profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/auth/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    token = _extract_token(authorization)
    site_store.logout(token or "")
    return {"message": "已退出当前账号。"}


@app.get("/api/auth/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_required_user)) -> MeResponse:
    user, profile = site_store.get_user_state(current_user["id"])
    return MeResponse(user=user, profile=profile)


@app.put("/api/auth/profile", response_model=MeResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: dict = Depends(get_required_user),
) -> MeResponse:
    try:
        user, profile = site_store.update_user_profile(
            current_user["id"],
            payload.avatar_data_url,
            payload.region,
        )
        return MeResponse(user=user, profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auth/dashboard", response_model=UserDashboardResponse)
async def user_dashboard(current_user: dict = Depends(get_required_user)) -> UserDashboardResponse:
    return UserDashboardResponse(**site_store.get_user_dashboard(current_user["id"]))


@app.get("/api/recommendations/videos", response_model=RecommendationResponse)
async def recommendation_videos(
    current_user: dict | None = Depends(get_optional_user),
) -> RecommendationResponse:
    bundle = site_store.get_recommendation_bundle(current_user["id"] if current_user else None)
    return RecommendationResponse(**bundle)


@app.put("/api/recommendations/preferences", response_model=RecommendationResponse)
async def update_preferences(
    payload: PreferenceUpdateRequest,
    current_user: dict = Depends(get_required_user),
) -> RecommendationResponse:
    try:
        bundle = site_store.update_preferences(current_user["id"], payload.preferred_topics)
        return RecommendationResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/recommendations/videos/{video_id}/action", response_model=RecommendationResponse)
async def video_action(
    video_id: str,
    payload: VideoActionRequest,
    current_user: dict = Depends(get_required_user),
) -> RecommendationResponse:
    try:
        bundle = site_store.record_video_action(current_user["id"], video_id, payload.action)
        return RecommendationResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/recommendations/videos/{video_id}/comments", response_model=RecommendationResponse)
async def video_comment(
    video_id: str,
    payload: RecommendationCommentCreateRequest,
    current_user: dict = Depends(get_required_user),
) -> RecommendationResponse:
    try:
        bundle = site_store.add_video_comment(current_user["id"], video_id, payload.content)
        return RecommendationResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/blog/posts", response_model=BlogResponse)
async def blog_posts() -> BlogResponse:
    return BlogResponse(**site_store.list_blog_posts())


@app.post("/api/blog/posts", response_model=BlogResponse)
async def create_blog_post(
    payload: BlogPostCreateRequest,
    current_user: dict = Depends(get_required_user),
) -> BlogResponse:
    try:
        _validate_blog_image(payload.image_data_url)
        bundle = site_store.create_blog_post(
            current_user["id"],
            payload.title,
            payload.content,
            payload.column,
            payload.image_data_url,
        )
        return BlogResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/blog/posts/{post_id}/like", response_model=BlogResponse)
async def toggle_blog_like(post_id: str, current_user: dict = Depends(get_required_user)) -> BlogResponse:
    try:
        bundle = site_store.toggle_blog_like(current_user["id"], post_id)
        return BlogResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/blog/posts/{post_id}/comments", response_model=BlogResponse)
async def create_blog_comment(
    post_id: str,
    payload: BlogCommentCreateRequest,
    current_user: dict = Depends(get_required_user),
) -> BlogResponse:
    try:
        bundle = site_store.add_blog_comment(current_user["id"], post_id, payload.content)
        return BlogResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/blog/posts/{post_id}", response_model=BlogResponse)
async def delete_blog_post(post_id: str, current_user: dict = Depends(get_required_user)) -> BlogResponse:
    try:
        bundle = site_store.delete_blog_post(current_user["id"], post_id)
        return BlogResponse(**bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
