from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


WasteCategory = Literal["可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾", "待确认"]
VideoAction = Literal["view", "like", "favorite"]


class DetectionItem(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    waste_category: WasteCategory
    rationale: str
    bbox: list[float]
    source: str = "视觉模型"


class PredictionResponse(BaseModel):
    source_image: str
    annotated_image: str
    detections: list[DetectionItem]
    summary_label: str
    summary_category: WasteCategory
    summary_reason: str
    recognition_mode: str
    model_name: str
    used_custom_weights: bool


class AnalyzeRequest(BaseModel):
    detections: list[DetectionItem]
    summary_label: str = ""
    summary_category: WasteCategory
    summary_reason: str
    recognition_mode: str = ""
    question: str = Field(
        default="请分析这张图片中的垃圾，并告诉我应该如何分类、投放和处理。"
    )


class AnalyzeResponse(BaseModel):
    answer: str
    provider: str


class UserProfile(BaseModel):
    id: str
    username: str
    created_at: str
    avatar_url: str = ""
    region: str = ""


class RecommendationProfile(BaseModel):
    preferred_topics: list[str] = Field(default_factory=list)
    liked_video_ids: list[str] = Field(default_factory=list)
    favorite_video_ids: list[str] = Field(default_factory=list)
    viewed_video_ids: list[str] = Field(default_factory=list)
    detection_history: list[str] = Field(default_factory=list)


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    message: str
    token: str
    user: UserProfile
    profile: RecommendationProfile


class MeResponse(BaseModel):
    user: UserProfile
    profile: RecommendationProfile


class RecommendationTopic(BaseModel):
    id: str
    label: str
    description: str


class RecommendationComment(BaseModel):
    id: str
    author_id: str
    author_name: str
    author_avatar_url: str = ""
    author_region: str = ""
    content: str
    created_at: str


class RecommendationVideo(BaseModel):
    id: str
    title: str
    description: str
    platform: str
    source: str
    duration: str
    url: str
    cover_image: str = ""
    topics: list[str]
    focus_categories: list[str]
    palette: list[str]
    featured: bool = False
    score: float = 0.0
    match_reason: str = ""
    comments: list[RecommendationComment] = Field(default_factory=list)
    liked: bool = False
    favorited: bool = False
    viewed: bool = False
    like_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0


class RecommendationResponse(BaseModel):
    topics: list[RecommendationTopic]
    videos: list[RecommendationVideo]
    profile: RecommendationProfile


class PreferenceUpdateRequest(BaseModel):
    preferred_topics: list[str] = Field(default_factory=list)


class VideoActionRequest(BaseModel):
    action: VideoAction


class RecommendationCommentCreateRequest(BaseModel):
    content: str


class BlogComment(BaseModel):
    id: str
    author_id: str
    author_name: str
    content: str
    created_at: str


class BlogPost(BaseModel):
    id: str
    author_id: str
    author_name: str
    title: str
    content: str
    column: str
    image_data_url: str = ""
    liked_user_ids: list[str] = Field(default_factory=list)
    comments: list[BlogComment] = Field(default_factory=list)
    created_at: str
    updated_at: str


class BlogResponse(BaseModel):
    columns: list[str]
    posts: list[BlogPost]


class BlogPostCreateRequest(BaseModel):
    title: str
    content: str
    column: str
    image_data_url: str = ""


class BlogCommentCreateRequest(BaseModel):
    content: str


class ProfileUpdateRequest(BaseModel):
    avatar_data_url: str = ""
    region: str = ""


class UserVideoCard(BaseModel):
    id: str
    title: str
    description: str
    platform: str
    source: str
    duration: str
    url: str
    cover_image: str = ""
    topics: list[str] = Field(default_factory=list)
    focus_categories: list[str] = Field(default_factory=list)


class UserCommentedVideo(BaseModel):
    comment_id: str
    video: UserVideoCard
    content: str
    created_at: str


class UserDashboardResponse(BaseModel):
    user: UserProfile
    profile: RecommendationProfile
    liked_videos: list[UserVideoCard] = Field(default_factory=list)
    commented_videos: list[UserCommentedVideo] = Field(default_factory=list)
    published_posts: list[BlogPost] = Field(default_factory=list)
