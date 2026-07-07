"""Zero-config skill pack (architecture §4.4 "开箱内置 100+ skill").

A catalog of skills the product searches at onboarding / runtime: Hermes kernel
capabilities, CLI-Anything harnesses, and Campus-specific skills. This is a **discovery
index**, not a set of installed binaries — each entry carries ``installed``/``maintained``
so reliability scoring reflects real availability. Names track real Hermes capabilities
and cli-anything-hub harnesses; campus entries are shipped with this package.
"""
from __future__ import annotations

from campus.meta_agent.types import SkillEntry

__all__ = ["build_manifest", "load_skill_pack", "SKILL_PACK_COUNT_MIN"]

SKILL_PACK_COUNT_MIN = 100

# (name, category) — Hermes kernel capabilities (available via the Hermes dependency).
_HERMES: list[tuple[str, str]] = [
    ("memory", "记忆"), ("kanban", "任务看板"), ("cron", "定时任务"), ("delegate", "子智能体委派"),
    ("skills", "技能管理"), ("search", "检索"), ("mcp", "协议扩展"), ("web_dashboard", "Web面板"),
    ("ui_tui", "终端界面"), ("gateway", "消息网关"), ("qqbot", "QQ机器人"), ("feishu", "飞书"),
    ("wecom", "企业微信"), ("telegram", "Telegram"), ("email_channel", "邮件渠道"),
    ("discord", "Discord"), ("slack", "Slack"), ("dingtalk", "钉钉"), ("weixin", "微信"),
    ("x_twitter", "X/Twitter"), ("reddit", "Reddit"), ("youtube", "YouTube"),
    ("bilibili", "哔哩哔哩"), ("github_tool", "GitHub"), ("filesystem", "文件系统"),
    ("shell", "命令行"), ("browser", "浏览器"), ("todo", "待办"), ("notes", "笔记"),
    ("calendar", "日历"), ("calculator", "计算器"), ("summarizer", "摘要"), ("translator", "翻译"),
    ("code_runner", "代码执行"),
]

# (name, category) — CLI-Anything harnesses (per-harness pip install; not auto-installed).
_CLI_ANYTHING: list[tuple[str, str]] = [
    ("libreoffice", "办公套件"), ("libreoffice_writer", "文档"), ("libreoffice_calc", "表格"),
    ("libreoffice_impress", "演示"), ("obsidian", "笔记"), ("zotero", "文献"), ("exa", "网页搜索"),
    ("godot", "游戏引擎"), ("comfyui", "AI绘图"), ("anki", "记忆卡片"), ("notion", "笔记"),
    ("typora", "Markdown"), ("logseq", "大纲笔记"), ("joplin", "笔记"), ("evernote", "笔记"),
    ("onenote", "笔记"), ("word", "文档"), ("excel", "表格"), ("powerpoint", "演示"),
    ("outlook", "邮件客户端"), ("pages", "文档"), ("numbers", "表格"), ("keynote", "演示"),
    ("preview", "PDF阅读"), ("vscode", "编辑器"), ("intellij", "IDE"), ("pycharm", "IDE"),
    ("vim", "编辑器"), ("emacs", "编辑器"), ("blender", "三维"), ("gimp", "图像编辑"),
    ("inkscape", "矢量绘图"), ("audacity", "音频编辑"), ("obs_studio", "直播录屏"),
    ("figma", "设计"), ("sketch", "设计"), ("ableton", "音乐制作"), ("reaper", "音频"),
    ("matlab", "科学计算"), ("mathematica", "科学计算"), ("rstudio", "统计"), ("jupyter", "笔记本"),
    ("postman", "API测试"), ("docker", "容器"), ("kubectl", "容器编排"), ("terraform", "基础设施"),
    ("ansible", "自动化运维"),
]

# (name, category) — Campus-specific skills (shipped in this package).
_CAMPUS: list[tuple[str, str]] = [
    ("research_web", "调研"), ("source_verify", "事实核查"), ("source_rank", "来源排序"),
    ("write_proposal", "写作"), ("write_ppt", "演示"), ("write_budget", "预算"),
    ("draft_email", "邮件草稿"), ("schedule_plan", "排期"), ("daily_quiz", "每日测验"),
    ("ebbinghaus_review", "复习"), ("persona_apply", "人格"), ("memory_recall", "记忆"),
    ("onboarding", "上手引导"), ("skill_discover", "技能发现"), ("model_route", "模型路由"),
    ("knowledge_scan", "知识扫描"), ("lecture_index", "讲义索引"), ("exam_plan", "复习计划"),
    ("birthday_remind", "提醒"), ("daily_log", "日志"), ("secretary_report", "汇报"),
    ("campus_news", "资讯"), ("course_platform", "课程平台"), ("grade_track", "成绩"),
    ("internship_search", "实习"), ("scholarship_search", "奖学金"), ("library_search", "图书馆"),
    ("print_queue", "打印"), ("cafeteria_menu", "食堂"), ("weather", "天气"),
    ("bus_schedule", "校车"), ("campus_map", "校园地图"), ("club_manage", "社团"),
    ("volunteer_log", "志愿时长"), ("sports_plan", "运动"), ("mental_check", "心理"),
    ("sleep_track", "睡眠"), ("focus_timer", "专注"), ("expense_track", "记账"),
    ("document_translate", "文档翻译"), ("citation_gen", "参考文献"),
]


def build_manifest() -> list[SkillEntry]:
    """Build the full skill catalog (>=100 entries)."""
    out: list[SkillEntry] = []
    for name, cat in _HERMES:
        out.append(SkillEntry(name=name, source="hermes", category=cat,
                              installed=True, maintained=True,
                              description=f"Hermes 内核能力：{cat}"))
    for name, cat in _CLI_ANYTHING:
        out.append(SkillEntry(name=name, source="cli_anything", category=cat,
                              installed=False, maintained=True,
                              description=f"CLI-Anything harness：{cat}（需安装）"))
    for name, cat in _CAMPUS:
        out.append(SkillEntry(name=name, source="campus", category=cat,
                              installed=True, maintained=True,
                              description=f"校园技能：{cat}"))
    return out


def load_skill_pack() -> list[SkillEntry]:
    """Convenience: build + sanity-check the manifest."""
    manifest = build_manifest()
    assert len(manifest) >= SKILL_PACK_COUNT_MIN, "skill pack must ship >=100 entries"
    return manifest
