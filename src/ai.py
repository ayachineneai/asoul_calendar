import json
from datetime import date

import anthropic

from bilibili.types import ClaudeConfig, Live, LiveKind
from bilibili.dynamics import DynamicDraw
from utils import parse_datetime, week_range


_SCHEDULE_CLASSIFIER_SYSTEM = (
    "你是一个动态分类助手。用户会给你一组B站动态文本，请判断哪条最可能附有本周直播日程表图片。"
    "只回复对应的序号数字，如果没有则回复-1。"
)

_SCHEDULE_PARSER_SYSTEM = """\
你是一个直播日程表解析助手，负责从图片中提取直播信息并以 JSON 数组返回。

## 成员信息
A-SOUL 是一个虚拟偶像团体，现有成员：
- 一期生：乃琳、嘉然、贝拉
- 二期生：思诺、心宜

## members 字段判断规则
1. 标题或标签含 "A-SOUL" 字样 → members 为一期生三人：["乃琳", "嘉然", "贝拉"]
2. 标题含多个成员名（如"心宜思诺"）→ members 仅为出现的成员，如 ["心宜", "思诺"]
3. 标题只含单个成员名，或标注为"XX直播" → members 为该成员，如 ["思诺"]
4. 无法判断 → members 为 []

## host 字段规则
- 直播间主体的原始文字，如 "A-SOUL游戏室"、"A-SOUL团综"、"思诺直播" 等
- 直接使用图片中出现的文字，不做推断

## tag 字段规则
- 从图片中每个条目的文字标签提取，常见值有："日常"、"节目"、"2D" 等
- 直接使用图片中出现的文字，不做推断
- 若该条目没有标签则为 ""

## 输出格式
只输出一个 JSON 数组，不含任何解释，格式如下：
[
  {
    "start_time": "2025-03-17 19:30:00",
    "host": "思诺直播",
    "title": "思诺100问7",
    "members": ["思诺"],
    "tag": "日常"
  }
]

## 约束
- 仔细扫描图片的每一行、每一列，不要遗漏任何条目
- start_time 格式严格为 YYYY-MM-DD HH:MM:SS
- 标注为"训练时间"或"休息日"的格子不输出
- title 使用图片中的原文，若有副标题一并包含，用空格连接
- 直接输出 JSON 数组，第一个字符必须是 `[`，最后一个字符必须是 `]`，不要加 markdown 代码块\
"""

def _find_schedule_index(client: anthropic.Anthropic, claude_config: ClaudeConfig, dynamics: list[DynamicDraw]) -> int:
    numbered = "\n\n".join(f"[{i}] {d.text}" for i, d in enumerate(dynamics))
    response = client.messages.create(
        model=claude_config.model,
        max_tokens=claude_config.max_tokens,
        system=_SCHEDULE_CLASSIFIER_SYSTEM,
        messages=[anthropic.types.MessageParam(role="user", content=numbered)],
    )
    return int(response.content[0].text.strip())


def _parse_schedule(client: anthropic.Anthropic, claude_config: ClaudeConfig, dynamic: DynamicDraw, week_start: date, week_end: date) -> list[Live]:
    image_contents = [
        {"type": "image", "source": {"type": "url", "url": url.replace("http://", "https://", 1)}}
        for url in dynamic.pics
    ]

    response = client.messages.create(
        model=claude_config.model,
        max_tokens=claude_config.max_tokens,
        system=_SCHEDULE_PARSER_SYSTEM,
        messages=[
            anthropic.types.MessageParam(
                role="user",
                content=[
                    *image_contents,
                    {
                        "type": "text",
                        "text": f"这是枝江娱乐本周（{week_start} 至 {week_end}）的直播日历图片，请解析所有直播条目。",
                    },
                ],
            )
        ],
    )

    raw = response.content[0].text.strip()
    return [
        Live(
            start_time=parse_datetime(item["start_time"]),
            host=item["host"],
            title=item["title"],
            members=item["members"],
            tag=item["tag"],
            kind=LiveKind.SCHEDULE,
        )
        for item in json.loads(raw)
    ]


def find_schedule_dynamic(claude_config: ClaudeConfig, dynamics: list[DynamicDraw], day: date) -> list[Live]:
    if not dynamics:
        return []

    client = anthropic.Anthropic(api_key=claude_config.api_key)

    index = _find_schedule_index(client, claude_config, dynamics)
    if index < 0:
        return []

    candidate = dynamics[index]
    return _parse_schedule(client, claude_config, candidate, *week_range(day))
