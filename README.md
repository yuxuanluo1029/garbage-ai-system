# EcoSort AI

EcoSort AI 是一个面向人工智能导论课程大作业的校园垃圾分类智能站，包含登录注册、垃圾识别、智能体问答、个性推荐、分类博客和个人信息页。

## 当前识别方案

- 视觉模型：自训练 YOLOv8s 四类垃圾检测模型
- 权重文件：`artifacts/weights/garbage4_best.pt`
- 检测类别：`recyclable waste / hazardous waste / kitchen waste / other waste`
- 中文输出：`可回收垃圾 / 有害垃圾 / 厨余垃圾 / 其他垃圾`
- 智能体：阿里云通义千问兼容 `chat/completions` 接口

## 本地启动

安装依赖：

```bash
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，填入自己的阿里云 API Key：

```env
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
LLM_API_KEY=你的阿里云APIKey
LLM_MODEL=qwen-plus
```

启动网页：

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 上传到 GitHub

第一次上传时，先在 GitHub 新建一个空仓库，不要勾选初始化 README、License 或 `.gitignore`。然后在本项目目录执行：

```bash
cd /d E:\人工智能\garbage_ai_system
git init
git add .
git commit -m "init garbage classification web app"
git branch -M main
git remote add origin https://github.com/你的用户名/garbage-ai-system.git
git push -u origin main
```

注意：`.env` 已经被 `.gitignore` 排除，不能把阿里云 API Key、密码或本地运行数据库传到 GitHub。

## Render 公网部署

Render 手动部署参数：

- Runtime：`Python 3`
- Build Command：`pip install -r requirements.txt`
- Start Command：`python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path：`/health`

必须在 Render 的 Environment 中配置：

```env
APP_TITLE=EcoSort AI
APP_HOST=0.0.0.0
VISION_BACKEND=ultralytics
VISION_MODEL_NAME=garbage4_best.pt
VISION_CONFIDENCE=0.25
VISION_IMGSZ=640
UPLOAD_DIR=./uploads
ARTIFACT_DIR=./artifacts
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
LLM_MODEL=qwen-plus
LLM_API_KEY=你的阿里云APIKey
```

仓库里已经提供 `render.yaml` 和 `.python-version`。如果使用 Render Blueprint，可以直接连接该仓库并同步配置；如果手动创建 Web Service，就按上面的 Build/Start 命令填写。

## 文件说明

```text
garbage_ai_system/
├─ app/                         # FastAPI 后端与静态前端
├─ artifacts/weights/            # 模型权重，默认保留 garbage4_best.pt
├─ scripts/                      # 训练辅助与说明书生成脚本
├─ uploads/                      # 本地上传文件，已排除 Git
├─ render.yaml                   # Render 部署配置
├─ .python-version               # Render Python 版本
├─ .env.example                  # 环境变量模板
└─ requirements.txt              # Python 依赖
```
