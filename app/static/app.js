const LOCAL_TOKEN_KEY = "ecosort.auth.token";
const SESSION_TOKEN_KEY = "ecosort.auth.session";
const REMEMBERED_USERNAME_KEY = "ecosort.auth.username";
const LOCAL_USER_KEY = "ecosort.auth.user";
const LOCAL_PROFILE_KEY = "ecosort.auth.profile";
const SESSION_USER_KEY = "ecosort.auth.session_user";
const SESSION_PROFILE_KEY = "ecosort.auth.session_profile";
const BLOG_IMAGE_MARKER = "[[博客配图]]";

const emptyProfile = () => ({
  preferred_topics: [],
  liked_video_ids: [],
  favorite_video_ids: [],
  viewed_video_ids: [],
  detection_history: [],
});

const emptyDashboard = () => ({
  user: null,
  profile: emptyProfile(),
  liked_videos: [],
  commented_videos: [],
  published_posts: [],
});

const state = {
  authMode: "login",
  activeSection: "detector",
  token: localStorage.getItem(LOCAL_TOKEN_KEY) || sessionStorage.getItem(SESSION_TOKEN_KEY) || "",
  currentUser: null,
  accountProfile: emptyProfile(),
  dashboard: emptyDashboard(),
  recommendations: {
    topics: [],
    videos: [],
    profile: emptyProfile(),
  },
  latestPrediction: null,
  selectedTopics: new Set(),
  blogColumns: [],
  blogPosts: [],
  blogFilter: "全部",
  blogImageDataUrl: "",
  profileAvatarDataUrl: "",
};

const authScreen = document.getElementById("auth-screen");
const siteShell = document.getElementById("site-shell");
const loginTab = document.getElementById("login-tab");
const registerTab = document.getElementById("register-tab");
const authSubmitButton = document.getElementById("auth-submit");
const authUsernameInput = document.getElementById("auth-username");
const authPasswordInput = document.getElementById("auth-password");
const rememberSessionInput = document.getElementById("remember-session");
const authHint = document.getElementById("auth-hint");
const topbarUsername = document.getElementById("topbar-username");
const topbarProfile = document.getElementById("topbar-profile");
const logoutButton = document.getElementById("logout-button");
const profileShortcut = document.getElementById("profile-shortcut");

const imageInput = document.getElementById("image-input");
const runButton = document.getElementById("run-button");
const analyzeButton = document.getElementById("analyze-button");
const statusText = document.getElementById("status-text");
const sourceImage = document.getElementById("source-image");
const annotatedImage = document.getElementById("annotated-image");
const summaryLabel = document.getElementById("summary-label");
const summaryCategory = document.getElementById("summary-category");
const summaryReason = document.getElementById("summary-reason");
const detectionsList = document.getElementById("detections-list");
const analysisOutput = document.getElementById("analysis-output");
const questionInput = document.getElementById("question-input");
const modelBadge = document.getElementById("model-badge");
const recognitionBadge = document.getElementById("recognition-badge");

const saveTopicsButton = document.getElementById("save-topics-button");
const topicChipGroup = document.getElementById("topic-chip-group");
const featuredVideoCover = document.getElementById("featured-video-cover");
const featuredVideoPlatform = document.getElementById("featured-video-platform");
const featuredVideoTitle = document.getElementById("featured-video-title");
const featuredVideoDesc = document.getElementById("featured-video-desc");
const featuredVideoTags = document.getElementById("featured-video-tags");
const featuredVideoReason = document.getElementById("featured-video-reason");
const featuredOpenButton = document.getElementById("featured-open-button");
const featuredLikeButton = document.getElementById("featured-like-button");
const featuredFavoriteButton = document.getElementById("featured-favorite-button");
const featuredCommentButton = document.getElementById("featured-comment-button");
const featuredVideoCommentInput = document.getElementById("featured-video-comment-input");
const featuredVideoComments = document.getElementById("featured-video-comments");
const recommendCount = document.getElementById("recommend-count");
const videoList = document.getElementById("video-list");

const blogTitleInput = document.getElementById("blog-title");
const blogColumnSelect = document.getElementById("blog-column");
const blogContentInput = document.getElementById("blog-content");
const blogImageInput = document.getElementById("blog-image-input");
const blogImagePreview = document.getElementById("blog-image-preview");
const publishBlogButton = document.getElementById("publish-blog-button");
const blogFilterRow = document.getElementById("blog-filter-row");
const blogPostList = document.getElementById("blog-post-list");
const blogSearchInput = document.getElementById("blog-search");

const profileAvatarPreview = document.getElementById("profile-avatar-preview");
const profileAvatarInput = document.getElementById("profile-avatar-input");
const profileUsernameInput = document.getElementById("profile-username");
const profileRegionInput = document.getElementById("profile-region");
const profileSaveButton = document.getElementById("profile-save-button");
const profileLikedCount = document.getElementById("profile-liked-count");
const profileCommentedCount = document.getElementById("profile-commented-count");
const profilePostCount = document.getElementById("profile-post-count");
const profileSummary = document.getElementById("profile-summary");
const profileLikedVideos = document.getElementById("profile-liked-videos");
const profileCommentedVideos = document.getElementById("profile-commented-videos");
const profileBlogPosts = document.getElementById("profile-blog-posts");

const channelButtons = [...document.querySelectorAll(".channel-button")];
const tabPanels = [...document.querySelectorAll(".tab-panel")];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(text) {
  statusText.textContent = text;
}

function readJsonStorage(storage, key, fallback = null) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    storage.removeItem(key);
    return fallback;
  }
}

function clearAuthSnapshot() {
  localStorage.removeItem(LOCAL_USER_KEY);
  localStorage.removeItem(LOCAL_PROFILE_KEY);
  sessionStorage.removeItem(SESSION_USER_KEY);
  sessionStorage.removeItem(SESSION_PROFILE_KEY);
}

function persistAuthSnapshot(user, profile, remember) {
  const target = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  target.setItem(remember ? LOCAL_USER_KEY : SESSION_USER_KEY, JSON.stringify(user));
  target.setItem(remember ? LOCAL_PROFILE_KEY : SESSION_PROFILE_KEY, JSON.stringify(profile || emptyProfile()));
  other.removeItem(remember ? SESSION_USER_KEY : LOCAL_USER_KEY);
  other.removeItem(remember ? SESSION_PROFILE_KEY : LOCAL_PROFILE_KEY);
}

function hydrateCachedAccount() {
  if (!state.token) {
    clearAuthSnapshot();
    return;
  }

  const user =
    readJsonStorage(localStorage, LOCAL_USER_KEY) || readJsonStorage(sessionStorage, SESSION_USER_KEY);
  const profile =
    readJsonStorage(localStorage, LOCAL_PROFILE_KEY, null) ||
    readJsonStorage(sessionStorage, SESSION_PROFILE_KEY, null) ||
    emptyProfile();

  if (user?.id) {
    state.currentUser = user;
    state.accountProfile = { ...emptyProfile(), ...profile };
  }
}

function tokenIsRemembered() {
  return Boolean(state.token && localStorage.getItem(LOCAL_TOKEN_KEY) === state.token);
}

function persistToken(token, remember) {
  state.token = token;
  if (remember) {
    localStorage.setItem(LOCAL_TOKEN_KEY, token);
    sessionStorage.removeItem(SESSION_TOKEN_KEY);
  } else {
    sessionStorage.setItem(SESSION_TOKEN_KEY, token);
    localStorage.removeItem(LOCAL_TOKEN_KEY);
  }
}

function clearToken() {
  state.token = "";
  localStorage.removeItem(LOCAL_TOKEN_KEY);
  sessionStorage.removeItem(SESSION_TOKEN_KEY);
  clearAuthSnapshot();
}

function resetUserState() {
  state.currentUser = null;
  state.accountProfile = emptyProfile();
  state.dashboard = emptyDashboard();
  state.profileAvatarDataUrl = "";
}

function resetWorkspaceState() {
  state.selectedTopics = new Set();
  state.blogFilter = "全部";
  state.blogImageDataUrl = "";
  state.profileAvatarDataUrl = "";
  state.latestPrediction = null;
  if (blogSearchInput) {
    blogSearchInput.value = "";
  }
  if (blogTitleInput) {
    blogTitleInput.value = "";
  }
  if (blogContentInput) {
    blogContentInput.value = "";
  }
  if (blogImagePreview) {
    blogImagePreview.classList.add("hidden");
    blogImagePreview.innerHTML = "";
  }
}

async function ensureSignedIn(message) {
  if (state.currentUser && state.token) {
    return true;
  }
  if (state.token) {
    await loadCurrentUser();
    if (state.currentUser) {
      return true;
    }
  }
  alert(message);
  return false;
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.includeAuth !== false && state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }
  if (options.jsonBody !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    body: options.jsonBody !== undefined ? JSON.stringify(options.jsonBody) : options.body,
  });

  const rawText = await response.text();
  let payload = {};
  try {
    payload = rawText ? JSON.parse(rawText) : {};
  } catch (error) {
    payload = { detail: rawText ? rawText.slice(0, 180) : "请求失败" };
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      resetUserState();
      renderShellState();
    }
    throw new Error(payload.detail || "请求失败");
  }
  return payload;
}

function setAuthMode(mode) {
  state.authMode = mode;
  loginTab.classList.toggle("is-active", mode === "login");
  registerTab.classList.toggle("is-active", mode === "register");
  authSubmitButton.textContent = mode === "login" ? "立即登录" : "创建账号";
  authHint.textContent =
    mode === "login"
      ? "登录后即可进入栏目式主站。"
      : "注册后会自动进入网站，并保存你的垃圾分类偏好和互动记录。";
}

function setActiveSection(section) {
  state.activeSection = section;
  channelButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.section === section);
  });
  tabPanels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === `${section}-panel`);
  });
  if (section === "recommend" && state.currentUser) {
    void loadRecommendations();
  }
  if (section === "blog" && state.currentUser) {
    void loadBlogPosts();
  }
  if (section === "profile" && state.currentUser) {
    void loadDashboard();
  }
}

function renderAvatarNode(element, avatarUrl, username) {
  if (!element) return;
  if (avatarUrl) {
    element.innerHTML = `<img src="${avatarUrl}" alt="${escapeHtml(username)}" />`;
  } else {
    element.textContent = String(username || "未").slice(0, 1).toUpperCase();
  }
}

function renderShellState() {
  const loggedIn = Boolean(state.currentUser && state.token);
  authScreen.classList.toggle("hidden", loggedIn);
  siteShell.classList.toggle("hidden", !loggedIn);

  if (loggedIn) {
    topbarUsername.textContent = state.currentUser.username;
    const regionLabel = state.currentUser.region ? `地区 ${state.currentUser.region}` : "地区未设置";
    topbarProfile.textContent = `偏好 ${state.accountProfile.preferred_topics.length} 项 · 历史 ${state.accountProfile.detection_history.length} 条 · ${regionLabel}`;
    renderAvatarNode(profileShortcut, state.currentUser.avatar_url, state.currentUser.username);
  } else {
    topbarUsername.textContent = "未登录";
    topbarProfile.textContent = "偏好 0 项 · 历史 0 条 · 地区未设置";
    renderAvatarNode(profileShortcut, "", "未");
    authUsernameInput.value = localStorage.getItem(REMEMBERED_USERNAME_KEY) || "";
    authPasswordInput.value = "";
  }
}

async function loadCurrentUser() {
  if (!state.token) {
    resetUserState();
    renderShellState();
    return;
  }

  try {
    const payload = await apiFetch("/api/auth/me");
    state.currentUser = payload.user;
    state.accountProfile = payload.profile;
    persistAuthSnapshot(payload.user, payload.profile, tokenIsRemembered());
  } catch (error) {
    clearToken();
    resetUserState();
    resetWorkspaceState();
  }
  renderShellState();
}

async function submitAuth() {
  const username = authUsernameInput.value.trim();
  const password = authPasswordInput.value.trim();

  if (!username || !password) {
    authHint.textContent = "请先填写用户名和密码。";
    return;
  }

  authSubmitButton.disabled = true;
  authHint.textContent = state.authMode === "login" ? "正在登录..." : "正在注册...";

  try {
    const payload = await apiFetch(`/api/auth/${state.authMode}`, {
      method: "POST",
      includeAuth: false,
      jsonBody: { username, password },
    });
    persistToken(payload.token, rememberSessionInput.checked);
    persistAuthSnapshot(payload.user, payload.profile, rememberSessionInput.checked);
    localStorage.setItem(REMEMBERED_USERNAME_KEY, username);
    resetWorkspaceState();
    state.currentUser = payload.user;
    state.accountProfile = payload.profile;
    renderShellState();
    setActiveSection("detector");
    await Promise.all([loadRecommendations(), loadBlogPosts(), loadDashboard()]);
  } catch (error) {
    const renderHint =
      state.authMode === "login" && /用户名或密码/.test(error.message)
        ? " 如果这是 Render 重新部署前注册的账号，免费实例的本地数据库可能已经被重置，需要重新注册；要长期保留账号需要给 Render 绑定持久磁盘。"
        : "";
    authHint.textContent = `${error.message}${renderHint}`;
  } finally {
    authSubmitButton.disabled = false;
  }
}

async function handleLogout() {
  logoutButton.disabled = true;
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } catch (error) {
    // ignore
  } finally {
    clearToken();
    resetUserState();
    resetWorkspaceState();
    state.blogPosts = [];
    state.recommendations = { topics: [], videos: [], profile: emptyProfile() };
    setActiveSection("detector");
    renderShellState();
    logoutButton.disabled = false;
  }
}

function renderTopicSelector() {
  const topics = state.recommendations.topics || [];
  topicChipGroup.innerHTML = topics
    .map(
      (topic) => `
        <button
          type="button"
          class="chip is-selectable ${state.selectedTopics.has(topic.id) ? "is-selected" : ""}"
          data-topic-id="${escapeHtml(topic.id)}"
          title="${escapeHtml(topic.description)}"
        >
          ${escapeHtml(topic.label)}
        </button>
      `,
    )
    .join("");

  topicChipGroup.querySelectorAll("[data-topic-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const topicId = button.dataset.topicId;
      if (!topicId) return;
      if (state.selectedTopics.has(topicId)) {
        state.selectedTopics.delete(topicId);
      } else {
        state.selectedTopics.add(topicId);
      }
      renderTopicSelector();
    });
  });
}

function buildVideoCover(video) {
  const palette = video.palette || ["#1f7a4d", "#2f9d63", "#d1f5dc"];
  const coverImage = video.cover_image
    ? `<img class="video-cover-image" src="${escapeHtml(video.cover_image)}" alt="${escapeHtml(video.title)}" />`
    : "";
  return `
    <div class="video-cover-inner" style="background:linear-gradient(135deg, ${palette.join(", ")})">
      ${coverImage}
      <div class="video-cover-overlay"></div>
      <div class="video-cover-content">
        <span class="video-cover-kicker">Verified Garbage Video</span>
        <div class="video-cover-title">${escapeHtml(video.title)}</div>
        <span class="video-pill" style="background:rgba(255,255,255,0.18); color:white;">${escapeHtml(video.duration)}</span>
      </div>
    </div>
  `;
}

function buildCommentAvatar(comment) {
  if (comment.author_avatar_url) {
    return `<span class="comment-avatar"><img src="${comment.author_avatar_url}" alt="${escapeHtml(comment.author_name)}" /></span>`;
  }
  return `<span class="comment-avatar">${escapeHtml(String(comment.author_name || "U").slice(0, 1).toUpperCase())}</span>`;
}

function buildInitialAvatar(name, className = "comment-avatar") {
  return `<span class="${className}">${escapeHtml(String(name || "U").slice(0, 1).toUpperCase())}</span>`;
}

function insertTextAtCursor(textarea, text) {
  const start = textarea.selectionStart ?? textarea.value.length;
  const end = textarea.selectionEnd ?? textarea.value.length;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  const prefix = before && !before.endsWith("\n") ? "\n\n" : "";
  const suffix = after && !after.startsWith("\n") ? "\n\n" : "";
  textarea.value = `${before}${prefix}${text}${suffix}${after}`;
  const cursor = before.length + prefix.length + text.length;
  textarea.focus();
  textarea.setSelectionRange(cursor, cursor);
}

function ensureBlogImageMarker() {
  if (!state.blogImageDataUrl) {
    return;
  }
  if (!blogContentInput.value.includes(BLOG_IMAGE_MARKER)) {
    insertTextAtCursor(blogContentInput, BLOG_IMAGE_MARKER);
  }
}

function renderInlineBlogImage(post) {
  if (!post.image_data_url) {
    return "";
  }
  return `
    <figure class="blog-inline-image">
      <img src="${post.image_data_url}" alt="${escapeHtml(post.title)}" />
      <figcaption>正文配图</figcaption>
    </figure>
  `;
}

function renderBlogBody(post) {
  const content = String(post.content || "");
  const imageHtml = renderInlineBlogImage(post);
  const parts = content.split(BLOG_IMAGE_MARKER);
  let imageInserted = false;

  const rendered = parts
    .map((part, index) => {
      const text = part.trim()
        ? `<p class="blog-post-content">${escapeHtml(part.trim()).replaceAll("\n", "<br />")}</p>`
        : "";
      if (index >= parts.length - 1 || !imageHtml || imageInserted) {
        return text;
      }
      imageInserted = true;
      return `${text}${imageHtml}`;
    })
    .join("");

  if (imageHtml && !imageInserted) {
    return `${rendered}${imageHtml}`;
  }
  return rendered || "<p class='blog-post-content'>这篇文章还没有正文内容。</p>";
}

function buildVideoComments(comments, limit = 2) {
  if (!comments?.length) {
    return "<div class='helper-text'>还没有人评论这条垃圾分类视频，你可以成为第一个留言的人。</div>";
  }
  return `
    <div class="video-comment-list">
      ${comments
        .slice(0, limit)
        .map(
          (comment) => `
            <div class="video-comment-card">
              <div class="video-comment-top">
                <div class="video-comment-author">
                  ${buildCommentAvatar(comment)}
                  <span>${escapeHtml(comment.author_name)}${comment.author_region ? ` · ${escapeHtml(comment.author_region)}` : ""}</span>
                </div>
                <span class="blog-meta">${new Date(comment.created_at).toLocaleString("zh-CN")}</span>
              </div>
              <div class="comment-content">${escapeHtml(comment.content)}</div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderFeaturedVideo(video) {
  if (!video) {
    featuredVideoCover.innerHTML = "";
    featuredVideoPlatform.textContent = "垃圾分类视频";
    featuredVideoTitle.textContent = "等待加载推荐";
    featuredVideoDesc.textContent = "登录后系统会给出与你的垃圾分类偏好有关的视频推荐。";
    featuredVideoTags.innerHTML = "";
    featuredVideoReason.textContent = "围绕垃圾分类精选推荐。";
    featuredVideoComments.innerHTML = "";
    featuredOpenButton.disabled = true;
    featuredLikeButton.disabled = true;
    featuredFavoriteButton.disabled = true;
    featuredCommentButton.disabled = true;
    featuredVideoCommentInput.disabled = true;
    featuredVideoCommentInput.value = "";
    return;
  }

  featuredVideoCover.innerHTML = buildVideoCover(video);
  featuredVideoPlatform.textContent = `${video.platform} · ${video.source}`;
  featuredVideoTitle.textContent = video.title;
  featuredVideoDesc.textContent = video.description;
  featuredVideoTags.innerHTML = [...video.topics, ...video.focus_categories]
    .slice(0, 6)
    .map((item) => `<span class="video-pill">${escapeHtml(item)}</span>`)
    .join("");
  featuredVideoReason.textContent = video.match_reason || "围绕垃圾分类精选推荐。";
  featuredVideoComments.innerHTML = buildVideoComments(video.comments || [], 3);

  featuredOpenButton.disabled = false;
  featuredLikeButton.disabled = false;
  featuredFavoriteButton.disabled = false;
  featuredCommentButton.disabled = false;
  featuredVideoCommentInput.disabled = false;
  featuredLikeButton.textContent = `${video.liked ? "已点赞" : "点赞"} ${video.like_count || 0}`;
  featuredFavoriteButton.textContent = `${video.favorited ? "已收藏" : "收藏"} ${video.favorite_count || 0}`;
  featuredCommentButton.textContent = `评论 ${video.comment_count || 0}`;
  featuredOpenButton.onclick = () => openVideo(video);
  featuredLikeButton.onclick = () => interactVideo(video.id, "like");
  featuredFavoriteButton.onclick = () => interactVideo(video.id, "favorite");
  featuredCommentButton.onclick = () => submitVideoComment(video.id, featuredVideoCommentInput);
}

function renderVideoList() {
  const videos = state.recommendations.videos || [];
  recommendCount.textContent = `${videos.length} 条视频`;
  if (!videos.length) {
    renderFeaturedVideo(null);
    videoList.innerHTML = "<div class='video-card'>当前没有可显示的垃圾分类视频推荐。</div>";
    return;
  }

  renderFeaturedVideo(videos[0]);
  videoList.innerHTML = videos
    .slice(1)
    .map(
      (video) => `
        <article class="video-card">
          <div class="video-card-layout">
            <div class="video-thumb">
              <img src="${escapeHtml(video.cover_image || "")}" alt="${escapeHtml(video.title)}" />
            </div>
            <div class="video-card-body">
              <div class="video-top">
                <div>
                  <div class="video-title">${escapeHtml(video.title)}</div>
                  <div class="blog-meta">${escapeHtml(video.platform)} · ${escapeHtml(video.source)} · 推荐分 ${escapeHtml(video.score)}</div>
                </div>
                <span class="state-badge">${escapeHtml(video.duration)}</span>
              </div>
              <p class="blog-post-content">${escapeHtml(video.description)}</p>
              <div class="chip-row">
                ${video.topics.map((topic) => `<span class="video-pill">${escapeHtml(topic)}</span>`).join("")}
              </div>
              <div class="chip-row">
                <span class="state-badge">点赞 ${video.like_count || 0}</span>
                <span class="state-badge">评论 ${video.comment_count || 0}</span>
              </div>
              <p class="recommend-reason">${escapeHtml(video.match_reason || "围绕垃圾分类学习路径精选")}</p>
              <div class="video-actions">
                <button class="primary-button video-open-button" type="button" data-video-id="${escapeHtml(video.id)}">打开视频</button>
                <button class="secondary-button video-like-button" type="button" data-video-id="${escapeHtml(video.id)}">${video.liked ? "已点赞" : "点赞"} ${video.like_count || 0}</button>
                <button class="secondary-button video-favorite-button" type="button" data-video-id="${escapeHtml(video.id)}">${video.favorited ? "已收藏" : "收藏"} ${video.favorite_count || 0}</button>
                <button class="secondary-button video-comment-button" type="button" data-video-id="${escapeHtml(video.id)}">评论 ${video.comment_count || 0}</button>
              </div>
            </div>
          </div>
          ${buildVideoComments(video.comments || [], 2)}
          <div class="comment-form video-comment-form">
            <input class="text-input comment-input" data-video-comment-input="${escapeHtml(video.id)}" type="text" placeholder="写下你对这条垃圾分类视频的看法" />
          </div>
        </article>
      `,
    )
    .join("");

  videoList.querySelectorAll(".video-open-button").forEach((button) => {
    button.addEventListener("click", () => {
      const video = videos.find((item) => item.id === button.dataset.videoId);
      if (video) {
        openVideo(video);
      }
    });
  });
  videoList.querySelectorAll(".video-like-button").forEach((button) => {
    button.addEventListener("click", () => interactVideo(button.dataset.videoId, "like"));
  });
  videoList.querySelectorAll(".video-favorite-button").forEach((button) => {
    button.addEventListener("click", () => interactVideo(button.dataset.videoId, "favorite"));
  });
  videoList.querySelectorAll(".video-comment-button").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.querySelector(`[data-video-comment-input="${button.dataset.videoId}"]`);
      void submitVideoComment(button.dataset.videoId, input);
    });
  });
}

async function loadRecommendations() {
  try {
    const payload = await apiFetch("/api/recommendations/videos");
    state.recommendations = payload;
    state.selectedTopics = new Set(payload.profile.preferred_topics || []);
    if (state.currentUser) {
      state.accountProfile = payload.profile;
      renderShellState();
    }
    renderTopicSelector();
    renderVideoList();
  } catch (error) {
    recommendCount.textContent = "推荐加载失败";
    videoList.innerHTML = `<div class="video-card">${escapeHtml(error.message)}</div>`;
  }
}

async function saveTopics() {
  if (!(await ensureSignedIn("请先登录后保存个性推荐偏好。"))) {
    return;
  }
  saveTopicsButton.disabled = true;
  try {
    const payload = await apiFetch("/api/recommendations/preferences", {
      method: "PUT",
      jsonBody: { preferred_topics: [...state.selectedTopics] },
    });
    state.recommendations = payload;
    state.accountProfile = payload.profile;
    renderShellState();
    renderTopicSelector();
    renderVideoList();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  } finally {
    saveTopicsButton.disabled = false;
  }
}

async function interactVideo(videoId, action) {
  if (!videoId) return;
  if (!(await ensureSignedIn("请先登录后再记录视频互动。"))) {
    return;
  }

  try {
    const payload = await apiFetch(`/api/recommendations/videos/${videoId}/action`, {
      method: "POST",
      jsonBody: { action },
    });
    state.recommendations = payload;
    state.accountProfile = payload.profile;
    renderShellState();
    renderTopicSelector();
    renderVideoList();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
}

async function submitVideoComment(videoId, inputElement) {
  if (!videoId) {
    return;
  }
  if (!(await ensureSignedIn("请先登录后再评论视频。"))) {
    return;
  }
  const content = inputElement?.value?.trim() || "";
  if (!content) {
    alert("请先输入评论内容。");
    return;
  }
  try {
    const payload = await apiFetch(`/api/recommendations/videos/${videoId}/comments`, {
      method: "POST",
      jsonBody: { content },
    });
    state.recommendations = payload;
    state.accountProfile = payload.profile;
    renderShellState();
    renderTopicSelector();
    renderVideoList();
    if (inputElement) {
      inputElement.value = "";
    }
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
}

async function openVideo(video) {
  if (state.currentUser) {
    try {
      await interactVideo(video.id, "view");
    } catch (error) {
      // ignore
    }
  }
  window.open(video.url, "_blank", "noopener,noreferrer");
}

function renderDetections(detections) {
  if (!detections.length) {
    detectionsList.innerHTML =
      "<div class='detection-card'>没有识别到稳定目标，请尝试单独拍摄主体、补光或更换角度。</div>";
    return;
  }

  detectionsList.innerHTML = detections
    .map(
      (item) => `
        <article class="detection-card">
          <div class="detection-top">
            <span class="detection-label">${escapeHtml(item.label)}</span>
            <span>${(item.confidence * 100).toFixed(1)}%</span>
          </div>
          <div class="detection-tag">${escapeHtml(item.waste_category)}</div>
          <div class="detection-source">识别来源：${escapeHtml(item.source)}</div>
          <div class="detection-reason">${escapeHtml(item.rationale)}</div>
        </article>
      `,
    )
    .join("");
}

async function runPrediction() {
  const file = imageInput.files?.[0];
  if (!file) {
    setStatus("请先选择一张垃圾图片。");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  setStatus("正在识别图片，请稍候...");
  runButton.disabled = true;

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "识别失败");
    }

    state.latestPrediction = payload;
    sourceImage.src = payload.source_image;
    annotatedImage.src = payload.annotated_image;
    summaryLabel.textContent = payload.summary_label;
    summaryCategory.textContent = payload.summary_category;
    summaryReason.textContent = payload.summary_reason;
    recognitionBadge.textContent = `识别链路：${payload.recognition_mode}`;
    modelBadge.textContent = `模型：${payload.model_name}`;
    renderDetections(payload.detections);
    analysisOutput.textContent = "识别完成。点击“生成分析”获取垃圾分类建议。";
    setStatus("识别完成。");

    await loadCurrentUser();
    await Promise.all([loadRecommendations(), loadDashboard()]);
  } catch (error) {
    setStatus(`识别失败：${error.message}`);
  } finally {
    runButton.disabled = false;
  }
}

async function runAnalysis() {
  if (!state.latestPrediction) {
    analysisOutput.textContent = "请先完成垃圾图片识别。";
    return;
  }

  analyzeButton.disabled = true;
  analysisOutput.textContent = "垃圾分类智能体正在分析，请稍候...";

  try {
    const payload = await apiFetch("/api/analyze", {
      method: "POST",
      jsonBody: {
        detections: state.latestPrediction.detections,
        summary_label: state.latestPrediction.summary_label,
        summary_category: state.latestPrediction.summary_category,
        summary_reason: state.latestPrediction.summary_reason,
        recognition_mode: state.latestPrediction.recognition_mode,
        question: questionInput.value.trim(),
      },
    });
    analysisOutput.textContent = `[${payload.provider}]\n\n${payload.answer}`;
  } catch (error) {
    analysisOutput.textContent = `分析失败：${error.message}`;
  } finally {
    analyzeButton.disabled = false;
  }
}

function resetDetectionPreview(file) {
  if (!file) return;
  sourceImage.src = URL.createObjectURL(file);
  annotatedImage.removeAttribute("src");
  summaryLabel.textContent = "待识别";
  summaryCategory.textContent = "待确认";
  summaryReason.textContent = "图片已加载，点击“开始识别”查看结果。";
  recognitionBadge.textContent = "识别链路未启动";
  modelBadge.textContent = "模型未加载";
  detectionsList.innerHTML = "";
  analysisOutput.textContent = "系统会根据识别结果和你的问题生成垃圾分类分析说明。";
  setStatus(`已选择图片：${file.name}`);
}

function renderBlogColumns() {
  const columns = state.blogColumns.length ? ["全部", ...state.blogColumns] : ["全部"];
  blogColumnSelect.innerHTML = state.blogColumns
    .map((column) => `<option value="${escapeHtml(column)}">${escapeHtml(column)}</option>`)
    .join("");
  blogFilterRow.innerHTML = columns
    .map(
      (column) => `
        <button
          type="button"
          class="chip is-selectable ${state.blogFilter === column ? "is-selected" : ""}"
          data-blog-filter="${escapeHtml(column)}"
        >
          ${escapeHtml(column)}
        </button>
      `,
    )
    .join("");

  blogFilterRow.querySelectorAll("[data-blog-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      state.blogFilter = button.dataset.blogFilter || "全部";
      renderBlogColumns();
      renderBlogPosts();
    });
  });
}

function getFilteredBlogPosts() {
  const keyword = blogSearchInput.value.trim().toLowerCase();
  return state.blogPosts.filter((post) => {
    const matchColumn = state.blogFilter === "全部" || post.column === state.blogFilter;
    if (!matchColumn) return false;
    if (!keyword) return true;
    return `${post.title}\n${post.content}\n${post.author_name}`.toLowerCase().includes(keyword);
  });
}

function renderBlogPosts() {
  const posts = getFilteredBlogPosts();
  if (!posts.length) {
    blogPostList.innerHTML = "<div class='blog-post-card'>当前筛选条件下没有垃圾分类文章。</div>";
    return;
  }

  blogPostList.innerHTML = posts
    .map((post) => {
      const ownPost = state.currentUser && post.author_id === state.currentUser.id;
      const liked = Boolean(state.currentUser && post.liked_user_ids.includes(state.currentUser.id));
      return `
        <article class="blog-post-card">
          <div class="blog-post-top">
            <div class="blog-author-line">
              ${buildInitialAvatar(post.author_name)}
              <div>
                <div class="blog-post-title">${escapeHtml(post.title)}</div>
                <div class="blog-meta">${escapeHtml(post.author_name)} · ${new Date(post.created_at).toLocaleString("zh-CN")}</div>
              </div>
            </div>
            <div class="blog-card-tools">
              <span class="blog-column-pill">${escapeHtml(post.column)}</span>
              ${ownPost ? `<button type="button" class="blog-action is-danger delete-post-button" data-post-id="${escapeHtml(post.id)}">删除</button>` : ""}
            </div>
          </div>
          <div class="blog-post-frame">
            ${renderBlogBody(post)}
          </div>
          <div class="blog-actions">
            <button type="button" class="blog-action like-post-button" data-post-id="${escapeHtml(post.id)}">${liked ? "已点赞" : "点赞"} ${post.liked_user_ids.length}</button>
            <span class="state-badge">评论 ${post.comments.length}</span>
          </div>
          <div class="comment-list">
            ${
              post.comments.length
                ? post.comments
                    .map(
                      (comment) => `
                        <div class="comment-card">
                          ${buildInitialAvatar(comment.author_name)}
                          <div class="comment-body">
                            <div class="comment-top">
                              <strong>${escapeHtml(comment.author_name)}</strong>
                              <span class="blog-meta">${new Date(comment.created_at).toLocaleString("zh-CN")}</span>
                            </div>
                            <div class="comment-content">${escapeHtml(comment.content)}</div>
                          </div>
                        </div>
                      `,
                    )
                    .join("")
                : "<div class='empty-comment'>还没有评论，可以先说一句“写得不错”。</div>"
            }
          </div>
          <div class="comment-form">
            <input class="text-input comment-input" data-comment-input="${escapeHtml(post.id)}" type="text" placeholder="写评论，简短回复也可以" />
            <button type="button" class="primary-button comment-submit-button" data-post-id="${escapeHtml(post.id)}">发表评论</button>
          </div>
        </article>
      `;
    })
    .join("");

  blogPostList.querySelectorAll(".like-post-button").forEach((button) => {
    button.addEventListener("click", () => toggleBlogLike(button.dataset.postId));
  });
  blogPostList.querySelectorAll(".comment-submit-button").forEach((button) => {
    button.addEventListener("click", () => submitComment(button.dataset.postId));
  });
  blogPostList.querySelectorAll(".delete-post-button").forEach((button) => {
    button.addEventListener("click", () => deletePost(button.dataset.postId));
  });
}

async function loadBlogPosts() {
  try {
    const payload = await apiFetch("/api/blog/posts");
    state.blogColumns = payload.columns || [];
    state.blogPosts = payload.posts || [];
    renderBlogColumns();
    renderBlogPosts();
  } catch (error) {
    blogPostList.innerHTML = `<div class="blog-post-card">${escapeHtml(error.message)}</div>`;
  }
}

async function readFileAsDataUrl(file, options = {}) {
  const rawDataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("图片读取失败"));
    reader.readAsDataURL(file);
  });

  if (!options.maxEdge || !file.type.startsWith("image/")) {
    return rawDataUrl;
  }

  return await new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const maxEdge = Number(options.maxEdge || 0);
      const ratio = Math.min(1, maxEdge / Math.max(image.width, image.height));
      const width = Math.max(1, Math.round(image.width * ratio));
      const height = Math.max(1, Math.round(image.height * ratio));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        resolve(rawDataUrl);
        return;
      }
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(image, 0, 0, width, height);

      const maxBytes = Number(options.maxBytes || 0);
      let quality = Number(options.quality || 0.82);
      let output = canvas.toDataURL("image/jpeg", quality);
      while (maxBytes && estimateDataUrlBytes(output) > maxBytes && quality > 0.46) {
        quality -= 0.08;
        output = canvas.toDataURL("image/jpeg", quality);
      }
      resolve(output);
    };
    image.onerror = () => reject(new Error("图片解析失败"));
    image.src = rawDataUrl;
  });
}

function estimateDataUrlBytes(dataUrl) {
  const base64 = String(dataUrl || "").split(",", 2)[1] || "";
  return Math.ceil((base64.length * 3) / 4);
}

async function handleBlogImagePick() {
  const file = blogImageInput.files?.[0];
  if (!file) return;
  try {
    state.blogImageDataUrl = await readFileAsDataUrl(file, {
      maxEdge: 900,
      quality: 0.76,
      maxBytes: 1.8 * 1024 * 1024,
    });
    const imageBytes = estimateDataUrlBytes(state.blogImageDataUrl);
    if (imageBytes > 2.2 * 1024 * 1024) {
      throw new Error("这张配图压缩后仍然偏大，请换一张更小的图片或截图后再上传。");
    }
    ensureBlogImageMarker();
    blogImagePreview.classList.remove("hidden");
    blogImagePreview.innerHTML = `
      <img src="${state.blogImageDataUrl}" alt="博客配图预览" />
      <div class="image-size-note">已自动压缩为 ${(imageBytes / 1024 / 1024).toFixed(2)} MB，并插入到正文当前位置。</div>
    `;
  } catch (error) {
    state.blogImageDataUrl = "";
    blogImageInput.value = "";
    blogImagePreview.classList.add("hidden");
    blogImagePreview.innerHTML = "";
    alert(error.message);
  }
}

async function publishBlog() {
  if (!(await ensureSignedIn("请先登录后发布博客。"))) {
    return;
  }

  publishBlogButton.disabled = true;
  try {
    if (!blogColumnSelect.value) {
      await loadBlogPosts();
    }
    if (!blogColumnSelect.value) {
      throw new Error("博客栏目还没有加载完成，请稍后再试。");
    }
    ensureBlogImageMarker();
    const payload = await apiFetch("/api/blog/posts", {
      method: "POST",
      jsonBody: {
        title: blogTitleInput.value.trim(),
        content: blogContentInput.value.trim(),
        column: blogColumnSelect.value,
        image_data_url: state.blogImageDataUrl,
      },
    });
    state.blogColumns = payload.columns || [];
    state.blogPosts = payload.posts || [];
    state.blogFilter = "全部";
    blogSearchInput.value = "";
    blogTitleInput.value = "";
    blogContentInput.value = "";
    state.blogImageDataUrl = "";
    blogImagePreview.classList.add("hidden");
    blogImagePreview.innerHTML = "";
    renderBlogColumns();
    renderBlogPosts();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  } finally {
    publishBlogButton.disabled = false;
  }
}

async function toggleBlogLike(postId) {
  if (!(await ensureSignedIn("请先登录后点赞博客。"))) {
    return;
  }
  try {
    const payload = await apiFetch(`/api/blog/posts/${postId}/like`, {
      method: "POST",
      jsonBody: {},
    });
    state.blogColumns = payload.columns || [];
    state.blogPosts = payload.posts || [];
    renderBlogPosts();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
}

async function submitComment(postId) {
  if (!(await ensureSignedIn("请先登录后发表评论。"))) {
    return;
  }
  const input = document.querySelector(`[data-comment-input="${postId}"]`);
  const content = input?.value?.trim() || "";
  if (!content) {
    alert("请先输入评论内容。");
    return;
  }
  try {
    const payload = await apiFetch(`/api/blog/posts/${postId}/comments`, {
      method: "POST",
      jsonBody: { content },
    });
    state.blogColumns = payload.columns || [];
    state.blogPosts = payload.posts || [];
    if (input) {
      input.value = "";
    }
    renderBlogPosts();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
}

async function deletePost(postId) {
  if (!(await ensureSignedIn("请先登录后删除博客。"))) return;
  if (!window.confirm("确认删除这篇垃圾分类博客吗？")) return;
  try {
    const payload = await apiFetch(`/api/blog/posts/${postId}`, { method: "DELETE" });
    state.blogColumns = payload.columns || [];
    state.blogPosts = payload.posts || [];
    renderBlogPosts();
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
}

function renderDashboard() {
  const user = state.dashboard.user || state.currentUser;
  if (!user) {
    renderAvatarNode(profileAvatarPreview, "", "未");
    profileUsernameInput.value = "";
    profileRegionInput.value = "";
    profileLikedCount.textContent = "0";
    profileCommentedCount.textContent = "0";
    profilePostCount.textContent = "0";
    profileSummary.textContent = "登录后系统会在这里汇总你的垃圾分类偏好、互动和发布记录。";
    profileLikedVideos.innerHTML = "<div class='profile-video-card'>当前还没有点赞视频。</div>";
    profileCommentedVideos.innerHTML = "<div class='profile-video-card'>当前还没有评论视频。</div>";
    profileBlogPosts.innerHTML = "<div class='profile-blog-card'>当前还没有发布博客。</div>";
    return;
  }

  const likedVideos = state.dashboard.liked_videos || [];
  const commentedVideos = state.dashboard.commented_videos || [];
  const publishedPosts = state.dashboard.published_posts || [];

  renderAvatarNode(profileAvatarPreview, state.profileAvatarDataUrl || user.avatar_url, user.username);
  profileUsernameInput.value = user.username || "";
  profileRegionInput.value = user.region || "";
  profileLikedCount.textContent = String(likedVideos.length);
  profileCommentedCount.textContent = String(commentedVideos.length);
  profilePostCount.textContent = String(publishedPosts.length);
  profileSummary.textContent = `当前已保存 ${state.accountProfile.preferred_topics.length} 个偏好标签，最近累计识别 ${state.accountProfile.detection_history.length} 次垃圾大类。`;

  profileLikedVideos.innerHTML = likedVideos.length
    ? likedVideos
        .map(
          (video) => `
            <div class="profile-video-card">
              <div class="profile-video-cover"><img src="${escapeHtml(video.cover_image || "")}" alt="${escapeHtml(video.title)}" /></div>
              <div class="profile-video-meta">
                <div class="profile-video-title">${escapeHtml(video.title)}</div>
                <div class="blog-meta">${escapeHtml(video.platform)} · ${escapeHtml(video.source)} · ${escapeHtml(video.duration)}</div>
                <div class="chip-row">
                  ${video.focus_categories.map((item) => `<span class="video-pill">${escapeHtml(item)}</span>`).join("")}
                </div>
                <a class="profile-link" href="${escapeHtml(video.url)}" target="_blank" rel="noreferrer">打开视频</a>
              </div>
            </div>
          `,
        )
        .join("")
    : "<div class='profile-video-card'>你还没有点赞任何垃圾分类视频。</div>";

  profileCommentedVideos.innerHTML = commentedVideos.length
    ? commentedVideos
        .map(
          (item) => `
            <div class="profile-video-card">
              <div class="profile-video-cover"><img src="${escapeHtml(item.video.cover_image || "")}" alt="${escapeHtml(item.video.title)}" /></div>
              <div class="profile-video-meta">
                <div class="profile-video-title">${escapeHtml(item.video.title)}</div>
                <div class="blog-meta">${new Date(item.created_at).toLocaleString("zh-CN")}</div>
                <div class="comment-content">${escapeHtml(item.content)}</div>
                <a class="profile-link" href="${escapeHtml(item.video.url)}" target="_blank" rel="noreferrer">回看视频</a>
              </div>
            </div>
          `,
        )
        .join("")
    : "<div class='profile-video-card'>你还没有评论任何垃圾分类视频。</div>";

  profileBlogPosts.innerHTML = publishedPosts.length
    ? publishedPosts
        .map(
          (post) => `
            <div class="profile-blog-card">
              <div class="blog-post-top">
                <div>
                  <div class="blog-post-title">${escapeHtml(post.title)}</div>
                  <div class="blog-meta">${escapeHtml(post.column)} · ${new Date(post.created_at).toLocaleString("zh-CN")}</div>
                </div>
                <button type="button" class="secondary-button profile-jump-blog-button" data-post-id="${escapeHtml(post.id)}">前往博客栏目</button>
              </div>
              <div class="blog-post-frame compact-frame">${renderBlogBody(post)}</div>
            </div>
          `,
        )
        .join("")
    : "<div class='profile-blog-card'>你还没有发布垃圾分类博客。</div>";

  profileBlogPosts.querySelectorAll(".profile-jump-blog-button").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveSection("blog");
      const target = state.blogPosts.find((post) => post.id === button.dataset.postId);
      if (target) {
        blogSearchInput.value = target.title;
        renderBlogPosts();
      }
    });
  });
}

async function loadDashboard() {
  if (!state.currentUser) {
    state.dashboard = emptyDashboard();
    renderDashboard();
    return;
  }
  try {
    const payload = await apiFetch("/api/auth/dashboard");
    state.dashboard = payload;
    if (payload.user) {
      state.currentUser = payload.user;
    }
    if (payload.profile) {
      state.accountProfile = payload.profile;
    }
    renderShellState();
    renderDashboard();
  } catch (error) {
    profileSummary.textContent = error.message;
  }
}

async function handleProfileAvatarPick() {
  const file = profileAvatarInput.files?.[0];
  if (!file) return;
  try {
    state.profileAvatarDataUrl = await readFileAsDataUrl(file, { maxEdge: 640, quality: 0.86 });
    renderAvatarNode(profileAvatarPreview, state.profileAvatarDataUrl, state.currentUser?.username || "U");
  } catch (error) {
    alert(error.message);
  }
}

async function saveProfile() {
  if (!(await ensureSignedIn("请先登录后再保存资料。"))) {
    return;
  }
  profileSaveButton.disabled = true;
  try {
    const payload = await apiFetch("/api/auth/profile", {
      method: "PUT",
      jsonBody: {
        avatar_data_url: state.profileAvatarDataUrl || state.currentUser.avatar_url || "",
        region: profileRegionInput.value.trim(),
      },
    });
    state.currentUser = payload.user;
    state.accountProfile = payload.profile;
    state.profileAvatarDataUrl = "";
    renderShellState();
    await Promise.all([loadRecommendations(), loadDashboard()]);
  } catch (error) {
    alert(error.message);
  } finally {
    profileSaveButton.disabled = false;
  }
}

async function initialize() {
  setAuthMode("login");
  setActiveSection("detector");
  hydrateCachedAccount();
  renderShellState();
  renderDashboard();
  await loadCurrentUser();
  if (state.currentUser) {
    await Promise.all([loadRecommendations(), loadBlogPosts(), loadDashboard()]);
  }
}

loginTab.addEventListener("click", () => setAuthMode("login"));
registerTab.addEventListener("click", () => setAuthMode("register"));
authSubmitButton.addEventListener("click", submitAuth);
logoutButton.addEventListener("click", handleLogout);
profileShortcut.addEventListener("click", () => setActiveSection("profile"));
runButton.addEventListener("click", runPrediction);
analyzeButton.addEventListener("click", runAnalysis);
saveTopicsButton.addEventListener("click", saveTopics);
publishBlogButton.addEventListener("click", publishBlog);
blogImageInput.addEventListener("change", handleBlogImagePick);
blogSearchInput.addEventListener("input", renderBlogPosts);
imageInput.addEventListener("change", () => resetDetectionPreview(imageInput.files?.[0]));
profileAvatarInput.addEventListener("change", handleProfileAvatarPick);
profileSaveButton.addEventListener("click", saveProfile);

channelButtons.forEach((button) => {
  button.addEventListener("click", () => setActiveSection(button.dataset.section));
});

initialize();
