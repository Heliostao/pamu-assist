"""
StarRailRes JSON → Markdown 转换器

从 Mar-7th/StarRailRes 仓库下载角色数据 JSON，
转换为人类可读的 Markdown 文件，供 RAG 使用。

用法: python json_to_md.py              # 生成全部角色
      python json_to_md.py --name 黄泉   # 仅生成指定角色（支持模糊匹配）
      python json_to_md.py --force       # 强制重新下载 JSON

输出: data/character/{角色名}.md
缓存: data/json/*.json
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

BASE_URL = "https://cdn.jsdelivr.net/gh/Mar-7th/StarRailRes@master/index_new/cn"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = PROJECT_ROOT / "data" / "json"
MD_DIR = PROJECT_ROOT / "data" / "character"

FILES = [
    "paths.json",
    "elements.json",
    "properties.json",
    "characters.json",
    "character_ranks.json",
    "character_skills.json",
    "character_skill_trees.json",
]

# 技能类型排序（Markdown 展示顺序）
SKILL_TYPE_ORDER = {
    "Normal": 0,
    "BPSkill": 1,
    "Ultra": 2,
    "Talent": 3,
    "Maze": 4,
    "MazeNormal": 5,
}

# 稀有度星星
RARITY_STAR = {4: "★★★★", 5: "★★★★★"}


# ═══════════════════════════════════════════════════════════════
# 下载
# ═══════════════════════════════════════════════════════════════

def download_json(filename: str, force: bool = False) -> dict:
    """下载单个 JSON 文件，已存在则跳过（除非 force=True）"""
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    filepath = JSON_DIR / filename

    if filepath.exists() and not force:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"{BASE_URL}/{filename}"
    print(f"  ↓ 下载 {filename} ...", end=" ")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GameLoreRAG/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"OK ({len(data)} 条)")
        return data
    except Exception as e:
        print(f"失败: {e}")
        raise


def download_all(force: bool = False) -> dict[str, dict]:
    """下载全部 7 个 JSON，返回 {文件名(不含.json): 数据}"""
    result = {}
    for f in FILES:
        key = f.replace(".json", "")
        result[key] = download_json(f, force=force)
    return result


# ═══════════════════════════════════════════════════════════════
# 映射表
# ═══════════════════════════════════════════════════════════════

def build_maps(data: dict) -> dict:
    """构建 ID→名称 映射表"""
    maps = {}

    # path id → 中文名
    maps["path"] = {}
    for k, v in data.get("paths", {}).items():
        maps["path"][k] = v.get("name", k)

    # element id → 中文名
    maps["element"] = {}
    for k, v in data.get("elements", {}).items():
        maps["element"][k] = v.get("name", k)

    # property type → 中文名
    maps["property"] = {}
    for k, v in data.get("properties", {}).items():
        pt = v.get("type", "")
        name = v.get("name", "")
        if pt and name:
            maps["property"][pt] = name
        maps["property"][k] = name or pt

    return maps


# ═══════════════════════════════════════════════════════════════
# 格式化工具
# ═══════════════════════════════════════════════════════════════

# 占位符正则: #数字[格式字母]
_PLACEHOLDER_RE = re.compile(r"#(\d+)\[([^\]]+)\]")


def replace_placeholders(desc: str, params: list) -> str:
    """将描述中的 #1[i] / #2[f1] 等占位符替换为实际数值

    规则：
    - 占位符后紧跟 % 则视为百分比（乘以100），否则显示原值
    - [i] → 整数，[f1] → 1位小数，[f2] → 2位小数
    - 参数索引从 1 开始（#1 = params[0]）
    """
    if not desc or not params:
        return desc

    def replacer(m: re.Match) -> str:
        idx_str = m.group(1)
        fmt = m.group(2)
        idx = int(idx_str) - 1  # 转为 0-based

        if idx < 0 or idx >= len(params):
            return m.group(0)  # 索引越界，保留原文

        val = params[idx]

        # 判断占位符后是否紧跟 %（用于百分比语义）
        end = m.end()
        is_pct = end < len(desc) and desc[end] == "%"

        if is_pct:
            # 百分比：乘以 100
            display_val = val * 100
        else:
            display_val = val

        # 格式化
        if fmt == "i":
            return str(int(round(display_val)))
        elif fmt == "f1":
            return f"{display_val:.1f}"
        elif fmt == "f2":
            return f"{display_val:.2f}"
        else:
            # 未知格式，保留原值
            return str(display_val)

    return _PLACEHOLDER_RE.sub(replacer, desc)


def replace_placeholders_minmax(desc: str, params_lv1: list, params_max: list) -> str:
    """将描述中的占位符替换为 最小值/最大值 格式（米游社风格）

    - 百分比 → 用中文括号包裹：【min%/max%】
    - 整数值不显示多余小数 (.0)
    - min == max 时只写一个值
    """
    if not desc or not params_lv1 or not params_max:
        return desc

    def fmt_val(v, fmt):
        """格式化数值，整数不掉小数"""
        if fmt == "i":
            return str(int(round(v)))
        elif fmt == "f1":
            if v == int(v):
                return str(int(v))
            return f"{v:.1f}"
        elif fmt == "f2":
            if v == int(v):
                return str(int(v))
            return f"{v:.2f}".rstrip("0").rstrip(".")
        else:
            return str(v)

    def replacer(m: re.Match) -> str:
        idx_str = m.group(1)
        fmt = m.group(2)
        idx = int(idx_str) - 1

        if idx < 0 or idx >= len(params_lv1) or idx >= len(params_max):
            return m.group(0)

        val_lv1 = params_lv1[idx]
        val_max = params_max[idx]

        end = m.end()
        is_pct = end < len(desc) and desc[end] == "%"

        if is_pct:
            display_lv1 = val_lv1 * 100
            display_max = val_max * 100
        else:
            display_lv1 = val_lv1
            display_max = val_max

        s_lv1 = fmt_val(display_lv1, fmt)
        s_max = fmt_val(display_max, fmt)

        # min == max → 只写一个（非百分比原样，百分比自己带%）
        if val_lv1 == val_max:
            if is_pct:
                return f"【{s_lv1}%】"
            return s_lv1

        # 百分比 → 【min%/max%】, 原文% 由后处理去掉
        if is_pct:
            return f"【{s_lv1}%/{s_max}%】"

        # 非百分比 → min/max
        return f"{s_lv1}/{s_max}"

    result = _PLACEHOLDER_RE.sub(replacer, desc)

    # 去掉百分比占位符后残留的原文字 %（%）, 如 【50%/140%】% → 【50%/140%】
    result = result.replace("】%", "】")

    return result


def fmt_skill_params(skill: dict) -> str:
    """从 skill.params 生成等级数值表"""
    params = skill.get("params", [])
    max_lv = skill.get("max_level", len(params))
    if not params or max_lv <= 1:
        return ""

    total_params = len(params[0]) if params else 0
    if total_params == 0:
        return ""

    # 按列判断语义：如果 level 1 是 float 且 0<v<=1，则整列为百分比列
    level1 = params[0]
    is_pct_col = []
    for v in level1:
        pct = isinstance(v, float) and 0 < v <= 1
        is_pct_col.append(pct)

    # 选取展示的等级
    show_levels = [1, 6, 10] if max_lv >= 10 else [1, max_lv]
    if max_lv >= 15:
        show_levels = [1, 8, 15]
    show_levels = [l for l in show_levels if l <= max_lv]

    # 表头
    param_headers = " | ".join(f"参数{i+1}" for i in range(total_params))
    header = f"| 等级 | {param_headers} |"
    sep = "|------|" + "|".join(["-"] * total_params) + "|"

    rows = []
    for lv in show_levels:
        vals = params[lv - 1]
        cells = []
        for i, v in enumerate(vals):
            if is_pct_col[i]:
                # 百分比列：1（int）→ 100%，0.5 → 50%
                pct_val = v * 100
                if pct_val == int(pct_val):
                    cells.append(f"{int(pct_val)}%")
                else:
                    cells.append(f"{pct_val:.1f}%")
            else:
                # 数值列：显示原始值
                if isinstance(v, float) and v == int(v):
                    cells.append(f"{int(v)}")
                else:
                    cells.append(str(v))
        row = " | ".join(cells)
        rows.append(f"| 等级{lv} | {row} |")

    return "\n".join([header, sep] + rows)


def fmt_rarity(rarity: int) -> str:
    return RARITY_STAR.get(rarity, "★" * rarity)


def fmt_path(path_id: str, maps: dict) -> str:
    return maps["path"].get(path_id, path_id)


def fmt_element(elem_id: str, maps: dict) -> str:
    return maps["element"].get(elem_id, elem_id)


def fmt_property(prop_type: str, value: float, maps: dict) -> str:
    """格式化属性加成文本"""
    name = maps.get("property", {}).get(prop_type, prop_type)
    # 判定百分比：类型名含比例关键字，或值在 0~1 之间（游戏内属性值 <1 的都是比率）
    is_pct = (
        "AddedRatio" in prop_type
        or "Resistance" in prop_type
        or "Critical" in prop_type and ("Damage" in prop_type or "Chance" in prop_type)
        or "Speed" in prop_type and "Ratio" in prop_type
    )
    if is_pct:
        return f"{name} +{value * 100:.0f}%"
    elif 0 < value < 1:
        # 兜底：值在 0~1 之间的浮点数一律当百分比处理
        return f"{name} +{value * 100:.0f}%"
    else:
        if value == int(value):
            return f"{name} +{int(value)}"
        else:
            return f"{name} +{value:.1f}"


# ═══════════════════════════════════════════════════════════════
# Markdown 生成
# ═══════════════════════════════════════════════════════════════

def gen_basic_info(char: dict, maps: dict) -> str:
    """基本信息表格"""
    name = char.get("name", "")
    if name == "{NICKNAME}":
        name = "开拓者"
    rarity = fmt_rarity(char.get("rarity", 5))
    path = fmt_path(char.get("path", ""), maps)
    element = fmt_element(char.get("element", ""), maps)

    lines = [
        f"## {name} 基本信息",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 稀有度 | {rarity} |",
        f"| 命途 | {path} |",
        f"| 战斗属性 | {element} |",
    ]

    tag = char.get("tag", "")
    if tag and tag != char.get("name", ""):
        lines.append(f"| 英文名 | {tag} |")

    max_sp = char.get("max_sp")
    if max_sp:
        lines.append(f"| 能量上限 | {max_sp} |")

    return "\n".join(lines)


def gen_skills(char: dict, skill_data: dict, maps: dict) -> str:
    """技能章节"""
    skill_ids = char.get("skills", [])
    if not skill_ids:
        return ""

    # 按类型排序
    skills = []
    for sid in skill_ids:
        s = skill_data.get(sid)
        if not s:
            continue
        stype = s.get("type", "")
        skills.append((SKILL_TYPE_ORDER.get(stype, 99), s))
    skills.sort(key=lambda x: x[0])

    # 去重：同名技能只保留官网完整版（simple_desc 最长者，同长度取 id 最大）。
    # StarRailRes 中部分角色存在同技能的多个条目：新旧两版（如花火 130607/1130607、
    # 藿藿 121704/1121704、黑天鹅 130701/1130701）或强化普攻分段（如乱破 131708/131710/131712）。
    # 实测官网当前文本 = 描述最完整（simple_desc 最长）的条目；旧版与"第3段"等子条目
    # 文本更短，会被自然淘汰。完全相同的重复条目取 id 最大的一个。
    # 注意：黄泉终结技子技能（啼泽雨斩/黄泉返渡）name 不同，不参与同名去重。
    # 此逻辑必须与 scripts/gen_testset.py 的 build_skill_questions 保持一致，
    # 否则测试集 ground_truth 会与 md 文本错位。
    seen_names = set()
    deduped = []
    for order, s in skills:
        key = (s.get("type", ""), s.get("name", ""))
        if key in seen_names:
            continue
        seen_names.add(key)
        candidates = [x for x in skills if (x[1].get("type", ""), x[1].get("name", "")) == key]
        best = max(
            candidates,
            key=lambda x: (
                len(x[1].get("simple_desc", "") or ""),
                int(x[1].get("id", "0") or 0),
            ),
        )
        deduped.append(best)
    skills = deduped

    type_labels = {
        "Normal": "普攻",
        "BPSkill": "战技",
        "Ultra": "终结技",
        "Talent": "天赋",
        "Maze": "秘技",
        "MazeNormal": "地图普攻",
    }

    name = char.get("name", "")
    if name == "{NICKNAME}":
        name = "开拓者"

    lines = [f"## {name} 技能"]
    for _, s in skills:
        name = s.get("name", "未知技能")
        stype = s.get("type", "")
        type_text = s.get("type_text") or type_labels.get(stype, stype)
        effect_text = s.get("effect_text", "")
        element = fmt_element(s.get("element", ""), maps) if s.get("element") else ""
        simple_desc = s.get("simple_desc", "")

        # 标题：技能名·类型
        header = f"### {name}"
        if type_text:
            header += f" · {type_text}"
        lines.append(header)

        # 元信息行
        meta_parts = []
        if effect_text:
            meta_parts.append(effect_text)
        if element:
            meta_parts.append(f"{element}属性")
        if meta_parts:
            lines.append("|".join(meta_parts))

        # 简介（等级 1 数值替换占位符）
        skill_params = s.get("params", [])
        if simple_desc:
            if skill_params:
                simple_desc = replace_placeholders(simple_desc, skill_params[0])
            lines.append(simple_desc)

        # 详细描述（占位符替换为 最小值/最大值，米游社风格）
        desc = s.get("desc", "")
        if desc:
            desc_clean = re.sub(r"<[^>]+>", "", desc)
            if skill_params and len(skill_params) >= 2:
                desc_clean = replace_placeholders_minmax(desc_clean, skill_params[0], skill_params[-1])
            elif skill_params:
                desc_clean = replace_placeholders(desc_clean, skill_params[0])
            if desc_clean.strip():
                lines.append(f"> {desc_clean}")

        # 技能间空行分隔
        lines.append("")

    return "\n".join(lines)


def gen_ranks(char: dict, rank_data: dict) -> str:
    """星魂章节"""
    rank_ids = char.get("ranks", [])
    if not rank_ids:
        return ""

    ranks = []
    for rid in rank_ids:
        r = rank_data.get(rid)
        if not r:
            continue
        ranks.append(r)
    ranks.sort(key=lambda x: x.get("rank", 0))

    if not ranks:
        return ""

    name = char.get("name", "")
    if name == "{NICKNAME}":
        name = "开拓者"

    lines = [f"## {name} 星魂"]
    for r in ranks:
        name = r.get("name", "")
        rank_num = r.get("rank", "?")
        desc = r.get("desc", "")
        lines.append(f"**{rank_num}·{name}** — {desc}")

    return "\n".join(lines)


def gen_skill_trees(char: dict, tree_data: dict, maps: dict) -> str:
    """行迹章节（额外能力 + 属性加成）"""
    tree_ids = char.get("skill_trees", [])
    if not tree_ids:
        return ""

    abilities = []  # 额外能力节点（有 name + desc）
    bonuses = []    # 属性加成节点（有 properties 无 desc）

    for tid in tree_ids:
        node = tree_data.get(tid)
        if not node:
            continue
        name = node.get("name", "")

        # 收集属性加成
        props = []
        for level in node.get("levels", []):
            for prop in level.get("properties", []):
                pt = prop.get("type", "")
                pv = prop.get("value", 0)
                props.append((pt, pv))

        if name and node.get("desc"):
            # 额外能力
            abilities.append({
                "name": name,
                "desc": node.get("desc", ""),
                "params": node.get("params", []),
            })
        elif props:
            # 属性加成（跳过基础技能节点，它们只有 level_up_skills）
            for pt, pv in props:
                if pv > 0:
                    bonuses.append((pt, pv))

    if not abilities and not bonuses:
        return ""

    name = char.get("name", "")
    if name == "{NICKNAME}":
        name = "开拓者"

    lines = [f"## {name} 行迹"]

    # 额外能力
    if abilities:
        lines.append(f"### {name} 额外能力")
        for ab in abilities:
            desc = ab.get("desc", "")
            # 清理 HTML
            desc = re.sub(r"<[^>]+>", "", desc)
            # 替换占位符
            ab_params = ab.get("params", [])
            if ab_params:
                desc = replace_placeholders(desc, ab_params[0])
            lines.append(f"**{ab['name']}** — {desc}")

    # 属性加成（去重 + 合并）
    if bonuses:
        lines.append(f"### {name} 属性加成")
        # 合并同类型加成
        merged = {}
        for pt, pv in bonuses:
            merged[pt] = merged.get(pt, 0) + pv
        for pt, total in merged.items():
            if total <= 0:
                continue
            label = fmt_property(pt, total, maps)
            lines.append(f"- {label}")

    return "\n".join(lines)


def gen_character_md(
    char_id: str,
    char: dict,
    data: dict,
    maps: dict,
) -> str:
    """为一个角色生成完整 Markdown"""
    name = char.get("name", char_id)
    if name == "{NICKNAME}":
        name = "开拓者"  # 主角占位符

    # 章节生成
    head = f"# {name}\n{gen_basic_info(char, maps)}"
    body_sections = [
        gen_skills(char, data.get("character_skills", {}), maps),
        gen_ranks(char, data.get("character_ranks", {})),
        gen_skill_trees(char, data.get("character_skill_trees", {}), maps),
    ]

    body = "\n\n".join(s for s in body_sections if s.strip())
    md = head + "\n\n" + body if body else head
    # 清理多余空行
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def find_characters(data: dict, name_filter: str | None = None) -> list[tuple[str, dict]]:
    """查找角色列表，支持模糊匹配"""
    chars = data.get("characters", {})
    if not name_filter:
        return list(chars.items())

    results = []
    for cid, c in chars.items():
        cname = c.get("name", "")
        if cname == "{NICKNAME}":
            cname = "开拓者"
        if name_filter.lower() in cname.lower() or name_filter.lower() in c.get("tag", "").lower():
            results.append((cid, c))
    return results


def main():
    # Windows CMD 环境下强制 UTF-8 输出
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    force = "--force" in sys.argv

    # 解析 --name 参数
    name_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--name" and i + 1 < len(sys.argv):
            name_filter = sys.argv[i + 1]
            break

    print("=" * 60)
    print("StarRailRes JSON → Markdown 转换器")
    print("=" * 60)

    # 1. 下载 JSON
    print("\n[1/4] 下载数据文件...")
    data = download_all(force=force)

    # 2. 构建映射
    print("\n[2/4] 构建 ID→名称 映射表...")
    maps = build_maps(data)
    print(f"  - 命途: {len(maps['path'])} 种")
    print(f"  - 战斗属性: {len(maps['element'])} 种")
    print(f"  - 属性: {len(maps['property'])} 种")

    # 3. 查找角色
    print("\n[3/4] 查找角色...")
    chars = find_characters(data, name_filter)
    if not chars:
        print(f"  未找到匹配 '{name_filter}' 的角色")
        return

    if name_filter:
        print(f"  匹配到 {len(chars)} 个角色: {', '.join(c.get('name', cid) for cid, c in chars)}")
    else:
        print(f"  共 {len(chars)} 个角色待生成")

    # 4. 生成 Markdown
    print("\n[4/4] 生成 Markdown...")
    MD_DIR.mkdir(parents=True, exist_ok=True)

    # 清空已有文件，确保重复运行时原地覆盖而非新增
    for old_file in MD_DIR.glob("*.md"):
        old_file.unlink()

    # 预处理：统计同名角色，为后续同名角色预留序号
    name_counts: dict[str, int] = {}
    for _, char in chars:
        name = char.get("name", "")
        if name == "{NICKNAME}":
            name = "开拓者"
        name_counts[name] = name_counts.get(name, 0) + 1

    generated = 0
    name_seq: dict[str, int] = {}
    for char_id, char in chars:
        name = char.get("name", char_id)
        if name == "{NICKNAME}":
            name = "开拓者"
        # 仅同名角色（如开拓者多个形态）加序号，唯一名称不加后缀
        if name_counts.get(name, 1) > 1:
            seq = name_seq.get(name, 0) + 1
            name_seq[name] = seq
            fname = f"{name}_{seq}"
        else:
            fname = name

        md = gen_character_md(char_id, char, data, maps)
        filepath = MD_DIR / f"{fname}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)
        generated += 1
        print(f"  [OK] {fname}.md")

    print(f"\n完成! 生成 {generated} 个角色 Markdown 文件。")
    print(f"JSON 缓存: {JSON_DIR}")
    print(f"Markdown:   {MD_DIR}")


if __name__ == "__main__":
    main()
