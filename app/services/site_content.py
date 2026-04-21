from __future__ import annotations

from copy import deepcopy


RECOMMENDATION_TOPICS = [
    {
        "id": "入门科普",
        "label": "入门科普",
        "description": "先快速理解四类垃圾的基本判定方法和常见误区。",
    },
    {
        "id": "校园投放",
        "label": "校园投放",
        "description": "围绕宿舍、教学楼、食堂等校园场景的正确投放方法。",
    },
    {
        "id": "可回收实践",
        "label": "可回收实践",
        "description": "重点关注纸箱、塑料盒、金属罐和玻璃瓶的回收实践。",
    },
    {
        "id": "厨余处理",
        "label": "厨余处理",
        "description": "聚焦果皮菜叶、剩饭剩菜和堆肥减量等内容。",
    },
    {
        "id": "有害垃圾",
        "label": "有害垃圾",
        "description": "聚焦废电池、过期药品、灯管等特殊垃圾的安全处理。",
    },
    {
        "id": "处理流程",
        "label": "处理流程",
        "description": "从前端分类到回收、运输、处理全链路进行理解。",
    },
]

DEFAULT_PREFERRED_TOPICS = ["入门科普", "校园投放"]

VIDEO_CATALOG = [
    {
        "id": "video-qa-3min",
        "title": "3分钟回答你对垃圾分类的所有疑问",
        "description": "把可回收物、有害垃圾、厨余垃圾和其他垃圾的判定逻辑一次讲清楚，适合作为入门视频。",
        "platform": "Bilibili",
        "source": "科普中国",
        "duration": "03:00",
        "url": "https://www.bilibili.com/video/BV1q4411w7s7/",
        "cover_image": "/static/video-covers/video-qa-3min.jpg",
        "topics": ["入门科普", "处理流程"],
        "focus_categories": ["可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾"],
        "palette": ["#123524", "#3E7B55", "#85A947"],
        "featured": True,
    },
    {
        "id": "video-campus-animation",
        "title": "生活垃圾分类知识动漫宣传片",
        "description": "通过动画形式讲校园、家庭和公共场所里最常见的分类规则，适合快速记忆。",
        "platform": "Bilibili",
        "source": "此号作废-cdss",
        "duration": "06:15",
        "url": "https://www.bilibili.com/video/BV1TZ4y1K7kw/",
        "cover_image": "/static/video-covers/video-campus-animation.jpg",
        "topics": ["入门科普", "校园投放"],
        "focus_categories": ["可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾"],
        "palette": ["#1E5128", "#4E9F3D", "#D8E9A8"],
        "featured": True,
    },
    {
        "id": "video-campus-short",
        "title": "垃圾分类科普短视频",
        "description": "面向校园日常投放的短时长科普视频，适合学生在课前或社团宣讲中快速播放。",
        "platform": "Bilibili",
        "source": "piaoranrprrpr",
        "duration": "01:47",
        "url": "https://www.bilibili.com/video/BV1Gh1jYdECM/",
        "cover_image": "/static/video-covers/video-campus-short.jpg",
        "topics": ["校园投放", "入门科普"],
        "focus_categories": ["可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾"],
        "palette": ["#16404D", "#4A9782", "#B6E2D3"],
        "featured": False,
    },
    {
        "id": "video-playful-sort",
        "title": "Segregation of Waste Garbage 寓教于乐科普视频",
        "description": "通过轻松的动画方式讲解垃圾分类和环境污染之间的关系，适合做趣味化推荐。",
        "platform": "Bilibili",
        "source": "Alberto_Chen__",
        "duration": "04:09",
        "url": "https://www.bilibili.com/video/BV1At411J7Yv/",
        "cover_image": "/static/video-covers/video-playful-sort.jpg",
        "topics": ["入门科普", "校园投放"],
        "focus_categories": ["可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾"],
        "palette": ["#5F0F40", "#9A031E", "#FB8B24"],
        "featured": False,
    },
    {
        "id": "video-processing-line",
        "title": "城市垃圾背后的流水线：分类、收集与处理",
        "description": "从回收、压缩、运输到分选处理，帮助用户理解垃圾分类后的去向和处理链路。",
        "platform": "Bilibili",
        "source": "Tb_green",
        "duration": "09:40",
        "url": "https://www.bilibili.com/video/BV1Uw411H7hk/",
        "cover_image": "/static/video-covers/video-processing-line.jpg",
        "topics": ["处理流程", "可回收实践"],
        "focus_categories": ["可回收垃圾", "其他垃圾"],
        "palette": ["#1F2041", "#4B3F72", "#FFC857"],
        "featured": True,
    },
    {
        "id": "video-kitchen-compost",
        "title": "厨余垃圾做堆肥方法分享",
        "description": "围绕果皮菜叶和剩饭剩菜的处理，讲解厨余减量、堆肥和资源化利用的思路。",
        "platform": "Bilibili",
        "source": "辉哥的耕读生活",
        "duration": "05:20",
        "url": "https://www.bilibili.com/video/BV1jf421q7pN/",
        "cover_image": "/static/video-covers/video-kitchen-compost.jpg",
        "topics": ["厨余处理", "处理流程"],
        "focus_categories": ["厨余垃圾"],
        "palette": ["#3B7A57", "#86B049", "#E3F09B"],
        "featured": False,
    },
    {
        "id": "video-smart-bin",
        "title": "智能分类垃圾桶",
        "description": "校园智能垃圾桶案例展示，适合对垃圾分类设备和 AI 场景感兴趣的用户。",
        "platform": "Bilibili",
        "source": "巡山徐",
        "duration": "02:10",
        "url": "https://www.bilibili.com/video/BV1UU4y1b7su/",
        "cover_image": "/static/video-covers/video-smart-bin.jpg",
        "topics": ["校园投放", "处理流程"],
        "focus_categories": ["可回收垃圾", "厨余垃圾", "有害垃圾", "其他垃圾"],
        "palette": ["#182848", "#4B6CB7", "#A7C7E7"],
        "featured": False,
    },
    {
        "id": "video-battery-hazard",
        "title": "干电池是有害垃圾吗？李永乐老师讲垃圾分类",
        "description": "围绕电池回收和有害垃圾展开，适合关注废电池、电子垃圾和特殊投放规则的用户。",
        "platform": "Bilibili",
        "source": "李永乐老师官方",
        "duration": "08:35",
        "url": "https://www.bilibili.com/video/av61134663",
        "cover_image": "/static/video-covers/video-battery-hazard.jpg",
        "topics": ["有害垃圾", "入门科普"],
        "focus_categories": ["有害垃圾"],
        "palette": ["#3C1518", "#69140E", "#D58936"],
        "featured": False,
    },
]

BLOG_COLUMNS = [
    "校园投放指南",
    "宿舍回收实践",
    "食堂厨余观察",
    "有害垃圾提醒",
    "分类误区拆解",
    "AI识别日志",
]

SEED_BLOG_POSTS = [
    {
        "title": "宿舍楼下分类桶总被投错，最该先补哪三步",
        "content": (
            "最近几周我连续观察了宿舍楼下的垃圾投放点，最常见的问题并不是学生完全不会分，"
            "而是桶身说明太抽象、桶位摆放不直观、夜间投放时缺少快速判断提示。真正有效的优化方式，"
            "往往是把苹果皮、奶茶杯、纸箱、废电池这类高频样本做成一张醒目的速查图，再配合桶位重排和错投提醒。"
        ),
        "column": "校园投放指南",
    },
    {
        "title": "苹果皮、橘子皮、剩饭剩菜为什么都该进厨余垃圾",
        "content": (
            "很多同学以为只要是吃过的东西就不能再分类，其实果皮菜叶、剩饭剩菜这类天然有机物，"
            "经过资源化处理后可以进入堆肥或厌氧消化链路。真正需要警惕的是被塑料袋、餐盒和纸巾混装后，"
            "厨余垃圾会被迫降级处理，所以分拣时一定要先去包装、再投放。"
        ),
        "column": "食堂厨余观察",
    },
    {
        "title": "废电池、过期药和灯管为什么一定不能混进普通垃圾",
        "content": (
            "有害垃圾最难的地方在于数量不大，却会直接影响后续处理安全。像钮扣电池、过期药品、"
            "废荧光灯管和含汞设备，一旦混进普通垃圾箱，不仅会造成后端分选困难，还可能带来土壤和渗滤液污染风险。"
            "校园里最稳妥的做法，是把这类物品集中到固定回收点并保持原包装完好。"
        ),
        "column": "有害垃圾提醒",
    },
    {
        "title": "纸箱、塑料盒和饮料瓶，为什么看起来像垃圾却最值得单独回收",
        "content": (
            "可回收垃圾并不是越脏越好丢，恰恰相反，纸箱、塑料盒、饮料瓶、金属罐和玻璃瓶越干净、越完整，"
            "越容易进入高价值回收流程。如果食物残渣和油污没有先处理掉，这些本来可以回收的材料很容易被当成其他垃圾处理。"
        ),
        "column": "宿舍回收实践",
    },
    {
        "title": "AI 垃圾识别系统上线后，我们最该关注的是哪些误判",
        "content": (
            "AI 识别能帮同学快速判断大类，但它最怕的是背景复杂、主体不清晰和标签语义过粗。"
            "比如同一张图里同时出现纸箱、塑料盒和果皮时，模型很可能只给出一个主类结果。"
            "因此系统页面除了显示最终判断，还应该保留检测明细、置信度和建议二次确认的场景。"
        ),
        "column": "AI识别日志",
    },
]

THEME_KEYWORDS = {
    "垃圾",
    "分类",
    "回收",
    "可回收",
    "厨余",
    "有害",
    "电池",
    "药品",
    "堆肥",
    "果皮",
    "塑料",
    "纸箱",
    "餐盒",
    "纸巾",
    "宿舍",
    "食堂",
    "环保",
    "投放",
    "低碳",
    "灯管",
    "易拉罐",
    "玻璃瓶",
    "金属",
    "资源化",
}

DETECTION_TOPIC_MAP = {
    "可回收垃圾": ["可回收实践", "校园投放"],
    "厨余垃圾": ["厨余处理", "校园投放"],
    "有害垃圾": ["有害垃圾", "处理流程"],
    "其他垃圾": ["入门科普", "校园投放"],
}


def contains_theme_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in THEME_KEYWORDS)


def sanitize_topics(raw_topics: list[str] | None) -> list[str]:
    valid = {item["id"] for item in RECOMMENDATION_TOPICS}
    ordered: list[str] = []
    for topic in raw_topics or []:
        if topic in valid and topic not in ordered:
            ordered.append(topic)
    return ordered or DEFAULT_PREFERRED_TOPICS.copy()


def default_profile() -> dict[str, list[str]]:
    return {
        "preferred_topics": DEFAULT_PREFERRED_TOPICS.copy(),
        "liked_video_ids": [],
        "favorite_video_ids": [],
        "viewed_video_ids": [],
        "detection_history": [],
    }


def build_recommendations(profile: dict[str, list[str]] | None) -> list[dict]:
    current = default_profile()
    if profile:
        current.update(
            {
                "preferred_topics": sanitize_topics(profile.get("preferred_topics")),
                "liked_video_ids": list(dict.fromkeys(profile.get("liked_video_ids", [])))[:30],
                "favorite_video_ids": list(dict.fromkeys(profile.get("favorite_video_ids", [])))[:30],
                "viewed_video_ids": list(dict.fromkeys(profile.get("viewed_video_ids", [])))[:30],
                "detection_history": list(dict.fromkeys(profile.get("detection_history", [])))[:8],
            }
        )

    preferred_topics = set(current["preferred_topics"])
    liked_ids = set(current["liked_video_ids"])
    favorite_ids = set(current["favorite_video_ids"])
    viewed_ids = set(current["viewed_video_ids"])
    recent_categories = current["detection_history"][:3]
    recent_topics = {
        topic
        for category in recent_categories
        for topic in DETECTION_TOPIC_MAP.get(category, [])
    }

    ranked: list[dict] = []
    for video in VIDEO_CATALOG:
        score = 42.0
        reasons: list[str] = []
        video_topics = set(video["topics"])
        focus_categories = set(video["focus_categories"])

        topic_hits = preferred_topics & video_topics
        if topic_hits:
            score += 18 + len(topic_hits) * 4
            reasons.append(f"匹配你的偏好标签：{'、'.join(sorted(topic_hits))}")

        recent_hits = recent_topics & video_topics
        if recent_hits:
            score += 16 + len(recent_hits) * 3
            reasons.append("结合你最近的识别结果做了优先推荐")

        if any(category in focus_categories for category in recent_categories):
            score += 8

        if video["id"] in liked_ids:
            score += 10
            reasons.append("你之前点赞过相近主题视频")
        if video["id"] in favorite_ids:
            score += 12
            reasons.append("你已收藏该类垃圾分类内容")
        if video["id"] in viewed_ids:
            score -= 4

        if video.get("featured"):
            score += 2

        item = deepcopy(video)
        item["score"] = round(score, 1)
        item["match_reason"] = "；".join(reasons[:2]) or "围绕垃圾分类学习路径精选"
        ranked.append(item)

    ranked.sort(key=lambda item: (item["score"], item.get("featured", False)), reverse=True)
    return ranked
