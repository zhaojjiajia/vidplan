from __future__ import annotations

import re
from typing import Any

from apps.ai.models import AITask
from apps.ai.services import (
    check_series_consistency,
    generate_episode_plan,
    generate_series_plan,
    generate_single_plan,
    optimize_plan,
)
from apps.assets.models import CharacterAsset, ColumnAsset, StyleAsset, WorldviewAsset
from apps.assets.serializers import (
    CharacterAssetSerializer,
    ColumnAssetSerializer,
    StyleAssetSerializer,
    WorldviewAssetSerializer,
)

from .models import SeriesPlan, VideoPlan
from .serializers import SeriesPlanSerializer, VideoPlanSerializer


ASSET_MODEL_BY_TYPE = {
    "characters": (CharacterAsset, CharacterAssetSerializer, "characters"),
    "styles": (StyleAsset, StyleAssetSerializer, "styles"),
    "worldviews": (WorldviewAsset, WorldviewAssetSerializer, "worldviews"),
    "columns": (ColumnAsset, ColumnAssetSerializer, "columns"),
}

AI_GENERATED_DIRECTIONS = {
    "ai_beauty",
    "ai_drama",
    "ai_animation",
    "ai_short_drama",
    "ai_kichiku",
    "text_to_video",
    "image_to_video",
    "virtual_ip",
}


def _content_or_default(ai_payload: dict) -> dict:
    """Pull `content` out of the AI payload, defending against non-dict values.

    Earlier versions also merged a `_ai_critique` from inline self-review here;
    critique now only runs via the explicit /review/ endpoint, so this helper
    is just a thin extraction.
    """
    content = ai_payload.get("content") or {}
    return content if isinstance(content, dict) else {}


def _content_with_direction_label(ai_payload: dict) -> dict:
    """Same as _content_or_default but lifts the AI-suggested
    `direction_label` into `content.direction_label` so the editor / card UI
    can display a richer Chinese name than the canonical 16-key label.
    Empty AI label → key omitted (frontend falls back to findDirectionLabel).
    """
    content = _content_or_default(ai_payload)
    label = (ai_payload.get("direction_label") or "").strip()
    if label:
        content = {**content, "direction_label": label}
    return content


def _safe_storyboard(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _parse_shot_duration(value: Any) -> int | None:
    if isinstance(value, (int, float)) and value > 0:
        return round(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|~|—|至|到)\s*(\d+(?:\.\d+)?)", text)
    if range_match:
        start = float(range_match.group(1))
        end = float(range_match.group(2))
        seconds = abs(end - start) or end
        return round(seconds) if seconds > 0 else None
    first = re.search(r"\d+(?:\.\d+)?", text)
    if not first:
        return None
    seconds = float(first.group(0))
    return round(seconds) if seconds > 0 else None


def _normalize_shot_duration(shot: dict) -> int:
    seconds = (
        _parse_shot_duration(shot.get("duration"))
        or _parse_shot_duration(shot.get("duration_seconds"))
        or _parse_shot_duration(shot.get("seconds"))
        or _parse_shot_duration(shot.get("time"))
    )
    return min(max(seconds or 3, 1), 600)


def _reindex_storyboard(shots: list[dict], *, start: int = 1) -> list[dict]:
    out = []
    for offset, shot in enumerate(shots):
        item = dict(shot)
        item["idx"] = start + offset
        item["duration"] = _normalize_shot_duration(item)
        out.append(item)
    return out


def _split_storyboard(shots: list[dict], count: int) -> list[list[dict]]:
    if count <= 0:
        return []
    base, extra = divmod(len(shots), count)
    chunks: list[list[dict]] = []
    cursor = 0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        chunks.append(shots[cursor:cursor + size])
        cursor += size
    return chunks


def _section_title(raw: dict, index: int) -> str:
    return _text(raw.get("title") or raw.get("name") or raw.get("heading")) or f"章节 {index + 1}"


def _section_summary(raw: dict) -> str:
    return _text(raw.get("summary") or raw.get("goal") or raw.get("description") or raw.get("note"))


def _sections_from_structure(structure: Any) -> list[dict]:
    if isinstance(structure, list):
        return [dict(item) for item in structure if isinstance(item, dict)]
    if isinstance(structure, dict):
        rows = []
        labels = {
            "hook": "开场",
            "body": "主体",
            "climax": "高潮",
            "ending": "结尾",
        }
        for key, label in labels.items():
            value = structure.get(key)
            if value:
                rows.append({"title": label, "summary": value})
        return rows
    return []


def _normalize_plan_sections(ai_payload: dict) -> dict:
    """确保新生成的方案具备 `content.sections[*].storyboard`。

    顶层 storyboard 继续保存为章节镜头的扁平副本，兼容导出、旧编辑器逻辑和一致性检查。
    """
    content = _content_with_direction_label(ai_payload)
    top_storyboard = _safe_storyboard(ai_payload.get("storyboard"))
    raw_sections = content.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raw_sections = _sections_from_structure(content.get("structure"))

    normalized: list[dict] = []
    section_shot_lists: list[list[dict]] = []
    if raw_sections:
        for index, raw in enumerate(raw_sections):
            if not isinstance(raw, dict):
                continue
            shots = _safe_storyboard(raw.get("storyboard"))
            section_shot_lists.append(shots)
            normalized.append({
                "title": _section_title(raw, index),
                "summary": _section_summary(raw),
                "duration": raw.get("duration") or raw.get("seconds") or "",
                "storyboard": shots,
            })

    if normalized and top_storyboard and not any(section_shot_lists):
        chunks = _split_storyboard(top_storyboard, len(normalized))
        for index, chunk in enumerate(chunks):
            normalized[index]["storyboard"] = chunk

    if not normalized:
        normalized = [{
            "title": "章节 1",
            "summary": content.get("positioning") or ai_payload.get("summary") or "",
            "duration": "",
            "storyboard": top_storyboard,
        }]

    flat_storyboard: list[dict] = []
    cursor = 1
    for section in normalized:
        shots = _reindex_storyboard(_safe_storyboard(section.get("storyboard")), start=cursor)
        section["storyboard"] = shots
        flat_storyboard.extend(shots)
        cursor += len(shots)

    content["sections"] = normalized
    ai_payload["content"] = content
    ai_payload["storyboard"] = flat_storyboard
    return ai_payload


def _strip_initial_storyboards(ai_payload: dict) -> dict:
    content = ai_payload.get("content")
    if isinstance(content, dict) and isinstance(content.get("sections"), list):
        sections = []
        for raw in content["sections"]:
            if not isinstance(raw, dict):
                continue
            sections.append({**raw, "storyboard": []})
        ai_payload["content"] = {**content, "sections": sections}
    ai_payload["storyboard"] = []
    return ai_payload


def _sync_sections_with_storyboard(content: Any, storyboard: Any) -> dict:
    if not isinstance(content, dict):
        return {}
    sections = content.get("sections")
    if not isinstance(sections, list) or not sections:
        return content
    shots = _safe_storyboard(storyboard)
    chunks = _split_storyboard(shots, len(sections))
    synced = []
    cursor = 1
    for index, raw in enumerate(sections):
        if not isinstance(raw, dict):
            continue
        chunk = _reindex_storyboard(chunks[index] if index < len(chunks) else [], start=cursor)
        cursor += len(chunk)
        synced.append({**raw, "storyboard": chunk})
    return {**content, "sections": synced}


def _storyboard_from_content_sections(content: Any) -> list[dict]:
    if not isinstance(content, dict):
        return []
    sections = content.get("sections")
    if not isinstance(sections, list):
        return []
    flat: list[dict] = []
    cursor = 1
    for section in sections:
        if not isinstance(section, dict):
            continue
        shots = _reindex_storyboard(_safe_storyboard(section.get("storyboard")), start=cursor)
        flat.extend(shots)
        cursor += len(shots)
    return flat


def _reindex_content_section_storyboards(content: Any) -> dict:
    if not isinstance(content, dict):
        return {}
    sections = content.get("sections")
    if not isinstance(sections, list):
        return content
    normalized = []
    cursor = 1
    for raw in sections:
        if not isinstance(raw, dict):
            continue
        shots = _reindex_storyboard(_safe_storyboard(raw.get("storyboard")), start=cursor)
        cursor += len(shots)
        normalized.append({**raw, "storyboard": shots})
    return {**content, "sections": normalized}


def _target_section_index_from_hint(hint: str) -> int | None:
    match = re.search(r"content\.sections\[(\d+)\]", hint or "")
    if not match:
        return None
    return int(match.group(1))


def _storyboard_from_target_section_payload(payload: dict, target_index: int) -> list[dict] | None:
    payload_content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
    sections = payload_content.get("sections")
    if isinstance(sections, list) and sections:
        candidates: list[Any] = []
        if 0 <= target_index < len(sections):
            candidates.append(sections[target_index])
        if len(sections) == 1:
            candidates.append(sections[0])

        for raw in candidates:
            if isinstance(raw, dict) and isinstance(raw.get("storyboard"), list):
                return _safe_storyboard(raw.get("storyboard"))

    if isinstance(payload.get("storyboard"), list):
        return _safe_storyboard(payload.get("storyboard"))
    return None


def _apply_target_section_storyboard(plan: VideoPlan, payload: dict, target_index: int) -> bool:
    content = plan.content if isinstance(plan.content, dict) else {}
    sections = content.get("sections")
    if not isinstance(sections, list) or not (0 <= target_index < len(sections)):
        return False

    shots = _storyboard_from_target_section_payload(payload, target_index)
    if shots is None:
        return False

    merged_sections: list[dict] = []
    for index, raw in enumerate(sections):
        section = dict(raw) if isinstance(raw, dict) else {}
        if index == target_index:
            section["storyboard"] = shots
        merged_sections.append(section)

    plan.content = _reindex_content_section_storyboards({**content, "sections": merged_sections})
    plan.storyboard = _storyboard_from_content_sections(plan.content)
    return True


def _resolve_direction(input_direction: str, ai_payload: dict) -> str:
    """Pick the routing key to store on the plan.

    - User filled it in the wizard → use that, period (don't let AI override).
    - User left it empty → use AI's inferred direction (already whitelisted
      to a canonical key by SinglePlanPayload's validator, or "" if AI also
      didn't know).
    """
    if (input_direction or "").strip():
        return input_direction
    return (ai_payload.get("direction") or "").strip()


def _content_with_series_direction_label(ai_payload: dict, visual_style: dict) -> dict:
    label = (ai_payload.get("direction_label") or "").strip()
    if not label:
        return visual_style
    return {**visual_style, "direction_label": label}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _asset_key(name: str) -> str:
    return "".join(name.lower().split())


def _asset_id_for_name(name: str, lookup: dict[str, dict[str, str]]) -> str:
    key = _asset_key(name)
    if not key:
        return ""
    for by_name in lookup.values():
        if key in by_name:
            return by_name[key]
    return ""


def _asset_ref_for_name(name: str, lookup: dict[str, dict[str, str]]) -> tuple[str, str]:
    key = _asset_key(name)
    if not key:
        return "", ""
    for atype, by_name in lookup.items():
        if key in by_name:
            return by_name[key], atype
    return "", ""


def _normalize_relationship_asset_type(value: Any) -> str:
    raw = _text(value).lower()
    aliases = {
        "character": "characters",
        "characters": "characters",
        "人物": "characters",
        "角色": "characters",
        "worldview": "worldviews",
        "worldviews": "worldviews",
        "environment": "worldviews",
        "environments": "worldviews",
        "环境": "worldviews",
        "小环境": "worldviews",
        "场景": "worldviews",
        "地点": "worldviews",
    }
    return aliases.get(raw, "")


def _normalize_series_relationships(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []

    rows = []
    for item in value:
        if isinstance(item, str):
            description = item.strip()
            if description:
                rows.append({"from": "", "to": "", "label": "", "description": description})
            continue
        if not isinstance(item, dict):
            continue
        from_name = _text(
            item.get("from") or item.get("from_") or item.get("source") or item.get("from_name")
            or item.get("from_asset_name")
        )
        to_name = _text(
            item.get("to") or item.get("target") or item.get("to_name") or item.get("to_asset_name")
        )
        label = _text(item.get("label") or item.get("relation") or item.get("relationship") or item.get("type"))
        description = _text(item.get("description") or item.get("note") or item.get("summary"))
        from_type = _normalize_relationship_asset_type(
            item.get("from_type") or item.get("from_asset_type") or item.get("source_type")
        )
        to_type = _normalize_relationship_asset_type(
            item.get("to_type") or item.get("to_asset_type") or item.get("target_type")
        )
        if not (from_name or to_name or label or description):
            continue
        rows.append(
            {
                "from": from_name,
                "to": to_name,
                "label": label,
                "description": description,
                "from_asset_name": _text(item.get("from_asset_name")) or from_name,
                "to_asset_name": _text(item.get("to_asset_name")) or to_name,
                "from_asset_type": from_type,
                "to_asset_type": to_type,
            }
        )
    return rows


def _list_of_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[\n;；、,，]", value) if item.strip()]
    return []


def _asset_specs(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_asset_bundle(value: Any) -> dict[str, list[dict]]:
    raw = value if isinstance(value, dict) else {}
    return {atype: _asset_specs(raw.get(atype)) for atype in ASSET_MODEL_BY_TYPE}


def _normalize_big_environment(value: Any, *, fallback_title: str, fallback_summary: str) -> dict:
    if isinstance(value, str):
        raw = {"description": value}
    elif isinstance(value, dict):
        raw = value
    else:
        raw = {}

    name = _text(raw.get("name") or raw.get("title"))
    description = _text(raw.get("description") or raw.get("background") or raw.get("summary"))
    tone_color = _text(raw.get("tone_color") or raw.get("tone") or raw.get("color"))
    images = raw.get("images") if isinstance(raw.get("images"), list) else []
    return {
        "name": name or "系列大环境",
        "description": description or fallback_summary or fallback_title or "所有角色共同所处的总体环境",
        "tone_color": tone_color,
        "rules": _list_of_text(raw.get("rules")),
        "locations": _list_of_text(raw.get("locations")),
        "images": images,
    }


def _big_environment_from_worldview_spec(spec: dict, *, fallback_title: str, fallback_summary: str) -> dict:
    payload = spec.get("payload") if isinstance(spec.get("payload"), dict) else {}
    fixed_traits = spec.get("fixed_traits") if isinstance(spec.get("fixed_traits"), list) else []
    raw = {
        "name": _text(spec.get("name")),
        "description": _text(
            payload.get("description")
            or payload.get("purpose")
            or payload.get("world_rules")
            or payload.get("setting")
            or payload.get("summary")
        ),
        "tone_color": _text(payload.get("tone_color") or payload.get("tone") or payload.get("color")),
        "rules": payload.get("rules") or payload.get("fixed_details") or fixed_traits,
        "locations": payload.get("locations") or payload.get("places") or payload.get("representative_locations"),
        "images": spec.get("images") if isinstance(spec.get("images"), list) else payload.get("images"),
    }
    return _normalize_big_environment(raw, fallback_title=fallback_title, fallback_summary=fallback_summary)


def _is_generic_big_environment(big_environment: dict) -> bool:
    generic_names = {
        "系列大环境",
        "大环境",
        "故事背景",
        "故事大环境",
        "背景环境",
        "总体环境",
        "主环境",
        "共同环境",
        "世界背景",
        "故事世界",
        "故事舞台",
        "系列背景",
    }
    return _text(big_environment.get("name")) in generic_names


def _worldview_text(spec: dict) -> str:
    payload = spec.get("payload") if isinstance(spec.get("payload"), dict) else {}
    fixed_traits = spec.get("fixed_traits") if isinstance(spec.get("fixed_traits"), list) else []
    values = [_text(spec.get("name"))]
    values.extend(_text(value) for value in payload.values() if not isinstance(value, (list, dict)))
    values.extend(_text(item) for item in fixed_traits)
    return " ".join(value for value in values if value)


def _is_small_environment_worldview(spec: dict) -> bool:
    text = _worldview_text(spec)
    small_keywords = [
        "居住",
        "住处",
        "家中",
        "家里",
        "家庭",
        "住家",
        "小屋",
        "房间",
        "出租屋",
        "卧室",
        "宿舍",
        "办公室",
        "工作间",
        "店",
        "小店",
        "基地",
        "实验室",
        "教室",
        "医院",
        "公司",
        "总部",
        "厨房",
        "车内",
    ]
    return any(keyword in text for keyword in small_keywords)


def _looks_like_big_environment_worldview(spec: dict) -> bool:
    if _is_small_environment_worldview(spec):
        return False
    text = _worldview_text(spec)
    broad_keywords = [
        "大环境",
        "世界",
        "背景",
        "森林",
        "校园",
        "城市",
        "都市",
        "小镇",
        "海边",
        "山谷",
        "乡村",
        "宇宙",
        "王国",
        "江湖",
        "赛博",
        "未来",
        "古代",
        "末世",
        "暗网",
        "社区",
        "狗熊岭",
    ]
    return any(keyword in text for keyword in broad_keywords)


def _promote_big_environment_from_worldviews(
    big_environment: dict,
    worldview_specs: list[dict],
    *,
    fallback_title: str,
    fallback_summary: str,
) -> tuple[dict, list[dict]]:
    if not worldview_specs or not _is_generic_big_environment(big_environment):
        return big_environment, worldview_specs

    candidate_index = next(
        (index for index, spec in enumerate(worldview_specs) if _looks_like_big_environment_worldview(spec)),
        0 if len(worldview_specs) == 1 else -1,
    )
    if candidate_index < 0:
        return big_environment, worldview_specs

    promoted = _big_environment_from_worldview_spec(
        worldview_specs[candidate_index],
        fallback_title=fallback_title,
        fallback_summary=fallback_summary,
    )
    return promoted, [spec for index, spec in enumerate(worldview_specs) if index != candidate_index]


def _is_big_environment_worldview(spec: dict, big_environment: dict) -> bool:
    name = _asset_key(_text(spec.get("name")))
    big_name = _asset_key(_text(big_environment.get("name")))
    if not name:
        return False
    generic_names = {"故事背景", "世界观", "大环境", "系列大环境", "背景环境", "故事世界", "故事舞台", "系列背景"}
    if _text(spec.get("name")) in generic_names or _looks_like_big_environment_worldview(spec):
        return True
    return bool(big_name and (name == big_name or name in big_name or big_name in name))


def _clean_character_name(value: Any) -> str:
    name = _text(value)
    name = re.sub(r"^[\d一二三四五六七八九十]+[.、]\s*", "", name)
    name = re.sub(r"[（(].*$", "", name).strip(" \t\r\n'\"“”‘’《》<>:：,，.。;；")
    blocked = ["序幕", "蜕变", "反转", "剧情", "大纲", "开场", "主体", "结尾", "能力", "环境", "系列", "故事"]
    if not (1 < len(name) <= 12) or any(word in name for word in blocked) or ("之" in name and len(name) > 4):
        return ""
    return name


def _append_character_name(names: list[str], value: Any) -> None:
    name = _clean_character_name(value)
    if name and name not in names:
        names.append(name)


def _extract_character_names_from_idea(idea: str, relationships: list[dict]) -> list[str]:
    names: list[str] = []
    for row in relationships:
        _append_character_name(names, row.get("from") or row.get("from_asset_name"))
        _append_character_name(names, row.get("to") or row.get("to_asset_name"))

    for match in re.finditer(r"(?:^|\n)\s*(?:[-*]\s*)?([^\n:：()（）]{2,12})(?:[（(][^）)]{0,40}[）)])?\s*[:：]", idea):
        _append_character_name(names, match.group(1))
    for match in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9·]{2,12})[（(](?:外号|代号|身份|角色)", idea):
        _append_character_name(names, match.group(1))
    for match in re.finditer(r"([\u4e00-\u9fff]{1,6}(?:老板|国王|队长|老师|医生|妈妈|爸爸|哥哥|姐姐|小姐|先生))", idea):
        _append_character_name(names, match.group(1))
    for match in re.finditer(r"([\u4e00-\u9fff]{2,4}强)(?=又|被|将|飞|用|从|像|把|直接|颤抖|误入|的)", idea):
        _append_character_name(names, match.group(1))
    return names[:8]


def _should_create_fallback_characters(direction: str, idea: str, relationships: list[dict]) -> bool:
    if relationships:
        return True
    if direction in AI_GENERATED_DIRECTIONS:
        return True
    narrative_keywords = ["剧情", "短剧", "动画", "角色", "人物", "主角", "反派", "连载", "世界观", "大纲"]
    return any(keyword in idea for keyword in narrative_keywords)


def _fallback_character_specs(idea: str, relationships: list[dict]) -> list[dict]:
    specs = []
    for name in _extract_character_names_from_idea(idea, relationships):
        specs.append(
            {
                "name": name,
                "payload": {"role": "主要角色", "appearance": "", "personality": "", "voice": ""},
                "fixed_traits": [],
            }
        )
    return specs


def _normalize_episode_asset_suggestions(value: Any, assets_dict: dict, big_environment: dict) -> dict[str, list[dict]]:
    raw = _normalize_asset_bundle(value)
    relation_source = value if isinstance(value, dict) else {}
    out: dict[str, list[dict]] = {"characters": [], "worldviews": [], "relationships": []}
    for atype in out:
        if atype == "relationships":
            continue
        existing_names = {
            _asset_key(_text(item.get("name")))
            for item in assets_dict.get(atype, [])
            if isinstance(item, dict) and _text(item.get("name"))
        }
        seen_names = set(existing_names)
        for spec in raw.get(atype, []):
            name = _text(spec.get("name"))[:120]
            key = _asset_key(name)
            if not name or not key or key in seen_names:
                continue
            if atype == "worldviews" and _is_big_environment_worldview(spec, big_environment):
                continue
            payload = spec.get("payload") if isinstance(spec.get("payload"), dict) else {}
            fixed_traits = spec.get("fixed_traits") if isinstance(spec.get("fixed_traits"), list) else []
            out[atype].append(
                {
                    "name": name,
                    "payload": payload,
                    "fixed_traits": fixed_traits,
                }
            )
            seen_names.add(key)
    out["relationships"] = [
        row for row in _normalize_series_relationships(relation_source.get("relationships"))
        if (row.get("from") or row.get("from_asset_name"))
        and (row.get("to") or row.get("to_asset_name"))
        and (row.get("label") or row.get("description"))
    ]
    return out


def _attach_relationship_asset_ids(
    rows: list[dict],
    lookup: dict[str, dict[str, str]],
) -> list[dict]:
    out = []
    for row in rows:
        from_name = row.get("from_asset_name") or row.get("from") or ""
        to_name = row.get("to_asset_name") or row.get("to") or ""
        enriched = dict(row)
        from_id, from_type = _asset_ref_for_name(from_name, lookup)
        to_id, to_type = _asset_ref_for_name(to_name, lookup)
        if from_id:
            enriched["from_asset_id"] = from_id
            if from_type:
                enriched["from_asset_type"] = from_type
        if to_id:
            enriched["to_asset_id"] = to_id
            if to_type:
                enriched["to_asset_type"] = to_type
        out.append(enriched)
    return out


def _resolve_category_and_ai_flag(
    input_direction: str,
    input_category: str,
    input_is_ai_video: bool,
    resolved_direction: str,
) -> tuple[str, bool]:
    """If the user supplied a direction the wizard already aligned category
    and is_ai_generated_video to it — trust those.
    If the user skipped direction and the AI inferred one, the original
    category/is_ai_video fields can be wrong (e.g. wizard defaulted to
    `real` but AI thinks it's `ai_short_drama`). Re-derive both from the
    resolved direction so the stored metadata stays internally consistent.
    """
    if (input_direction or "").strip():
        return input_category, input_is_ai_video
    is_ai = resolved_direction in AI_GENERATED_DIRECTIONS
    category = (
        VideoPlan.Category.AI_GENERATED if is_ai else VideoPlan.Category.REAL
    )
    return category, is_ai or input_is_ai_video


def execute_ai_task(task: AITask) -> dict:
    handlers = {
        AITask.TaskType.GENERATE_PLAN: execute_generate_plan_task,
        AITask.TaskType.OPTIMIZE_PLAN: execute_optimize_plan_task,
        AITask.TaskType.GENERATE_SERIES: execute_generate_series_task,
        AITask.TaskType.GENERATE_EPISODE: execute_generate_episode_task,
        AITask.TaskType.CHECK_CONSISTENCY: execute_check_consistency_task,
    }
    handler = handlers.get(task.task_type)
    if handler is None:
        raise ValueError(f"Unsupported AI task type: {task.task_type}")
    return handler(task)


def execute_generate_plan_task(task: AITask) -> dict:
    data = task.input_payload
    ai_payload = generate_single_plan(
        user=task.user,
        direction=data["direction"],
        idea=data["idea"],
        is_ai_generated_video=data["is_ai_generated_video"],
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        duration_seconds=data.get("duration_seconds", 30),
        style=data.get("style", ""),
    )
    ai_payload = _normalize_plan_sections(ai_payload)
    ai_payload = _strip_initial_storyboards(ai_payload)
    resolved_direction = _resolve_direction(data["direction"], ai_payload)
    resolved_category, resolved_is_ai_video = _resolve_category_and_ai_flag(
        input_direction=data["direction"],
        input_category=data["category"],
        input_is_ai_video=data["is_ai_generated_video"],
        resolved_direction=resolved_direction,
    )
    plan = VideoPlan.objects.create(
        user=task.user,
        title=ai_payload.get("title", "未命名方案")[:200],
        direction=resolved_direction,
        category=resolved_category,
        is_ai_generated_video=resolved_is_ai_video,
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        duration_seconds=data.get("duration_seconds", 30),
        style=data.get("style", ""),
        summary=ai_payload.get("summary", ""),
        content=ai_payload.get("content", {}),
        storyboard=ai_payload.get("storyboard", []),
        editing_advice=ai_payload.get("editing_advice", {}),
        ai_prompts=ai_payload.get("ai_prompts", {}),
    )
    return {"plan_id": str(plan.id), "title": plan.title}


def execute_optimize_plan_task(task: AITask) -> dict:
    data = task.input_payload
    plan = VideoPlan.objects.get(pk=data["plan_id"], user=task.user)
    scope = data.get("scope", "full")
    hint = data.get("hint", "")
    current = dict(VideoPlanSerializer(plan).data)
    series_context = _series_context_for_plan(plan)
    if series_context:
        current["_series_context"] = series_context
    ai_payload = optimize_plan(user=task.user, plan_dict=current, scope=scope, hint=hint)
    apply_ai_payload(plan, ai_payload, scope=scope, hint=hint)
    if plan.status == VideoPlan.Status.OPTIMIZING:
        plan.status = VideoPlan.Status.DRAFT
    plan.save()
    return {"plan_id": str(plan.id), "title": plan.title, "scope": scope}


def _series_context_for_plan(plan: VideoPlan) -> dict | None:
    if not plan.series_id:
        return None
    series = plan.series
    positioning = series.positioning if isinstance(series.positioning, dict) else {}
    related_episodes = series.episodes.exclude(pk=plan.pk).order_by("episode_order", "created_at", "id")[:8]
    return {
        "title": series.title,
        "summary": series.summary,
        "direction": series.direction,
        "target_audience": series.target_audience,
        "positioning": positioning,
        "relationships": positioning.get("relationships", []),
        "episode_template": series.episode_template,
        "visual_style": series.visual_style,
        "assets": collect_assets(series),
        "episodes": [
            {
                "title": episode.title,
                "summary": episode.summary,
                "episode_order": episode.episode_order,
            }
            for episode in related_episodes
        ],
    }


def execute_generate_series_task(task: AITask) -> dict:
    data = task.input_payload
    auto_create = data.get("auto_create_assets", True)
    ai_payload = generate_series_plan(
        user=task.user,
        direction=data["direction"],
        idea=data["idea"],
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        update_frequency=data.get("update_frequency", "周更"),
        episode_duration_seconds=data.get("episode_duration_seconds", 60),
        planned_episodes=data.get("planned_episodes", 10),
        style=data.get("style", ""),
    )
    resolved_direction = _resolve_direction(data["direction"], ai_payload)
    positioning = ai_payload.get("positioning", {})
    if not isinstance(positioning, dict):
        positioning = {}
    asset_bundle = _normalize_asset_bundle(ai_payload.get("assets"))
    big_environment = _normalize_big_environment(
        positioning.get("big_environment") or ai_payload.get("big_environment"),
        fallback_title=ai_payload.get("title", ""),
        fallback_summary=ai_payload.get("summary", ""),
    )
    relationships = _normalize_series_relationships(
        ai_payload.get("relationships") or positioning.get("relationships") or []
    )
    big_environment, asset_bundle["worldviews"] = _promote_big_environment_from_worldviews(
        big_environment,
        asset_bundle["worldviews"],
        fallback_title=ai_payload.get("title", ""),
        fallback_summary=ai_payload.get("summary", ""),
    )
    positioning = {**positioning, "big_environment": big_environment, "relationships": relationships}
    series = SeriesPlan.objects.create(
        user=task.user,
        title=ai_payload.get("title", "未命名系列")[:200],
        direction=resolved_direction,
        summary=ai_payload.get("summary", ""),
        target_platform=data.get("target_platform", "抖音"),
        target_audience=data.get("target_audience", ""),
        update_frequency=data.get("update_frequency", "周更"),
        episode_duration_seconds=data.get("episode_duration_seconds", 60),
        planned_episodes=data.get("planned_episodes", 10),
        positioning=positioning,
        episode_template=ai_payload.get("episode_template", {}),
        visual_style=_content_with_series_direction_label(
            ai_payload,
            ai_payload.get("visual_style", {}) if isinstance(ai_payload.get("visual_style", {}), dict) else {},
        ),
        title_style=ai_payload.get("title_style", {}),
        initial_topics=ai_payload.get("initial_topics", []),
    )

    created_asset_count = 0
    created_asset_lookup: dict[str, dict[str, str]] = {
        "characters": {},
        "worldviews": {},
    }
    if auto_create:
        if not asset_bundle["characters"] and _should_create_fallback_characters(
            resolved_direction,
            data.get("idea", ""),
            relationships,
        ):
            asset_bundle["characters"] = _fallback_character_specs(data.get("idea", ""), relationships)
        for atype, (model_cls, _ser, m2m_name) in ASSET_MODEL_BY_TYPE.items():
            created_asset_ids = []
            for spec in asset_bundle.get(atype, []):
                if atype == "worldviews" and _is_big_environment_worldview(spec, big_environment):
                    continue
                name = (spec.get("name") or "").strip()[:120] or "未命名"
                payload = spec.get("payload") or {}
                fixed_traits = spec.get("fixed_traits") or []
                asset = model_cls.objects.create(
                    user=task.user,
                    name=name,
                    payload=payload if isinstance(payload, dict) else {},
                    fixed_traits=fixed_traits if isinstance(fixed_traits, list) else [],
                )
                if atype in created_asset_lookup:
                    created_asset_lookup[atype][_asset_key(name)] = str(asset.pk)
                created_asset_ids.append(asset.pk)
            if created_asset_ids:
                getattr(series, m2m_name).set(created_asset_ids)
                created_asset_count += len(created_asset_ids)

    if relationships:
        series.positioning = {
            **(series.positioning or {}),
            "relationships": _attach_relationship_asset_ids(relationships, created_asset_lookup),
        }
        series.save(update_fields=["positioning", "updated_at"])

    return {"series_id": str(series.id), "title": series.title, "created_asset_count": created_asset_count}


def _next_episode_order(series: SeriesPlan) -> int:
    current = series.episodes.order_by("-episode_order", "-created_at").values_list("episode_order", flat=True).first()
    return int(current or 0) + 1


def execute_generate_episode_task(task: AITask) -> dict:
    data = task.input_payload
    series = SeriesPlan.objects.get(pk=data["series_id"], user=task.user)
    series_dict = SeriesPlanSerializer(series).data
    assets_dict = collect_assets(series)
    previous_episodes = collect_previous_episode_memory(series)
    ai_payload = generate_episode_plan(
        user=task.user,
        series_dict=series_dict,
        assets_dict=assets_dict,
        topic=data["topic"],
        episode_goal=data.get("episode_goal", ""),
        extra=data.get("extra_requirements", ""),
        previous_episodes=previous_episodes,
    )
    ai_payload = _normalize_plan_sections(ai_payload)
    ai_payload = _strip_initial_storyboards(ai_payload)
    positioning = series.positioning if isinstance(series.positioning, dict) else {}
    asset_suggestions = _normalize_episode_asset_suggestions(
        ai_payload.get("asset_suggestions")
        or (ai_payload.get("content", {}) if isinstance(ai_payload.get("content"), dict) else {}).get("asset_suggestions"),
        assets_dict,
        positioning.get("big_environment", {}) if isinstance(positioning.get("big_environment"), dict) else {},
    )

    is_ai_direction = series.direction in AI_GENERATED_DIRECTIONS
    plan = VideoPlan.objects.create(
        user=task.user,
        series=series,
        title=ai_payload.get("title", data["topic"])[:200],
        # Episode direction always inherits the series direction — that's the
        # whole point of the series. AI's direction_label still survives via
        # _content_with_direction_label so each episode can show a richer name.
        direction=series.direction,
        category=VideoPlan.Category.AI_GENERATED if is_ai_direction else VideoPlan.Category.REAL,
        is_ai_generated_video=is_ai_direction,
        target_platform=series.target_platform,
        target_audience=series.target_audience,
        duration_seconds=series.episode_duration_seconds,
        style="",
        summary=ai_payload.get("summary", ""),
        content=ai_payload.get("content", {}),
        storyboard=ai_payload.get("storyboard", []),
        editing_advice=ai_payload.get("editing_advice", {}),
        ai_prompts=ai_payload.get("ai_prompts", {}),
        episode_order=_next_episode_order(series),
    )
    return {
        "plan_id": str(plan.id),
        "series_id": str(series.id),
        "title": plan.title,
        "asset_suggestions": asset_suggestions,
    }


def execute_check_consistency_task(task: AITask) -> dict:
    data = task.input_payload
    series = SeriesPlan.objects.get(pk=data["series_id"], user=task.user)
    series_dict = SeriesPlanSerializer(series).data
    assets_dict = collect_assets(series)

    episode_qs = series.episodes.order_by("episode_order", "created_at", "id")
    if data.get("plan_id"):
        episode_qs = episode_qs.filter(pk=data["plan_id"])
    episodes_list = [VideoPlanSerializer(e).data for e in episode_qs]

    if not episodes_list:
        return {"score": 100, "issues": []}

    return check_series_consistency(
        user=task.user,
        series_dict=series_dict,
        assets_dict=assets_dict,
        episodes_list=episodes_list,
    )


def apply_ai_payload(plan: VideoPlan, payload: dict, *, scope: str = "", hint: str = "") -> None:
    target_section_index = _target_section_index_from_hint(hint) if scope == "storyboard" else None
    if target_section_index is not None and _apply_target_section_storyboard(plan, payload, target_section_index):
        return

    content_sections_updated = False
    if "title" in payload:
        plan.title = payload["title"][:200] or plan.title
    if "summary" in payload:
        plan.summary = payload["summary"]
    if "content" in payload:
        payload_content = payload["content"] if isinstance(payload["content"], dict) else {}
        content_sections_updated = isinstance(payload_content.get("sections"), list)
        plan.content = {**plan.content, **payload_content} if isinstance(plan.content, dict) else payload_content
        if content_sections_updated:
            plan.content = _reindex_content_section_storyboards(plan.content)
        section_storyboard = _storyboard_from_content_sections(plan.content)
        if content_sections_updated or section_storyboard:
            plan.storyboard = section_storyboard
    if "storyboard" in payload and not content_sections_updated:
        plan.storyboard = payload["storyboard"]
        plan.content = _sync_sections_with_storyboard(plan.content, plan.storyboard)
    if "editing_advice" in payload:
        plan.editing_advice = payload["editing_advice"]
    if "ai_prompts" in payload:
        plan.ai_prompts = payload["ai_prompts"]


def collect_assets(series: SeriesPlan) -> dict:
    out: dict[str, list[dict]] = {}
    for atype, (_model, ser_cls, m2m_name) in ASSET_MODEL_BY_TYPE.items():
        out[atype] = [ser_cls(a).data for a in getattr(series, m2m_name).all()]
    return out


def collect_previous_episode_memory(series: SeriesPlan, limit: int = 5) -> list[dict]:
    episodes = list(series.episodes.order_by("-episode_order", "-created_at")[:limit])
    memory: list[dict] = []
    for episode in reversed(episodes):
        shots = episode.storyboard if isinstance(episode.storyboard, list) else []
        memory.append({
            "title": episode.title,
            "summary": episode.summary,
            "status": episode.status,
            "storyboard_brief": [
                {
                    "idx": shot.get("idx"),
                    "description": shot.get("description") or shot.get("visual") or "",
                }
                for shot in shots[:3]
                if isinstance(shot, dict)
            ],
        })
    return memory
