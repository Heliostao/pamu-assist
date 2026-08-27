"""
模板生成 RAG 评估测试集（零 LLM 成本）。

从 data/json/ 的结构化数据（characters / character_ranks / character_skills）
按模板生成 question + ground_truth + target_role，输出到 eval_data/testset.jsonl。

ground_truth 选材规则（保证与知识库 md 原文逐字一致，供检索结果做 content 匹配）：
- 星魂问题：character_ranks[id].desc（已验证与 md "**N·名称** — desc" 逐字一致）
- 技能问题：character_skills[id].simple_desc（json 的 desc 含 #1[i]% 参数占位符，
  与 md 的【50%/140%】不一致，不能用；simple_desc 与 md 首段逐字一致）

只生成"存在对应 md 文件"的角色，保证每条测试样本都有正样本可命中。
"""
import argparse
import json

import random
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.util.config import PROJECT_ROOT as CFG_ROOT  # noqa: E402

PROJECT_ROOT = Path(CFG_ROOT)
DATA_DIR = PROJECT_ROOT / "data"
JSON_DIR = DATA_DIR / "json"
CHAR_DIR = DATA_DIR / "character"
EVAL_DIR = PROJECT_ROOT / "eval_data"

# 角色 id 前缀 → 星级：characters.json 的 key 即角色 id，
# character_ranks.json / character_skills.json 的 key 前 4 位即所属角色 id。
ROLE_ID_PREFIX_LEN = 4


def _load_json(name: str) -> dict:
    with open(JSON_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _md_role_names() -> set[str]:
    """知识库中实际存在的角色 md 文件名集合（不含扩展名）。"""
    if not CHAR_DIR.exists():
        return set()
    return {p.stem for p in CHAR_DIR.glob("*.md")}


def build_rank_questions(
    characters: dict, ranks: dict, md_roles: set[str]
) -> list[dict]:
    """星魂问题："{角色名}的星魂效果是什么？" ground_truth=rank.desc。"""
    samples = []
    for role_id, role in characters.items():
        name = role.get("name", "")
        if name not in md_roles:
            continue
        for rank_id in role.get("ranks", []):
            rank = ranks.get(rank_id)
            if not rank or not rank.get("desc"):
                continue
            samples.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": "rank",
                    "question": f"{name}的星魂效果是什么？",
                    "ground_truth": rank["desc"],
                    "target_role": name,
                }
            )
    return samples


def _dedup_skills(skill_ids: list[str], skills: dict) -> list[dict]:
    """与 crawler/json_to_md.py 的 gen_skills 去重保持一致：
    同 (type, name) 只保留官网完整版（simple_desc 最长，同长取 id 最大），
    保证测试集 ground_truth 与 md 文本逐字对齐。
    注意：两处逻辑必须同步修改。
    """
    picked: dict[tuple[str, str], tuple[int, dict]] = {}
    for sid in skill_ids:
        s = skills.get(sid)
        if not s or not s.get("simple_desc"):
            continue
        key = (s.get("type", ""), s.get("name", ""))
        score = (
            len(s.get("simple_desc", "") or ""),
            int(s.get("id", "0") or 0),
        )
        if key not in picked or score > picked[key][0]:
            picked[key] = (score, s)
    return [s for _, s in picked.values()]


def build_skill_questions(
    characters: dict, skills: dict, md_roles: set[str]
) -> list[dict]:
    """技能问题："{角色名}的{type_text}效果是什么？" ground_truth=skill.simple_desc。"""
    samples = []
    for role_id, role in characters.items():
        name = role.get("name", "")
        if name not in md_roles:
            continue
        for skill in _dedup_skills(role.get("skills", []), skills):
            type_text = skill.get("type_text", "技能")
            samples.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": "skill",
                    "question": f"{name}的{type_text}效果是什么？",
                    "ground_truth": skill["simple_desc"],
                    "target_role": name,
                }
            )
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="模板生成 RAG 评估测试集（零 LLM 成本）")
    parser.add_argument("--size", type=int, default=50, help="抽样条数（默认 50，0=全量）")
    parser.add_argument("--seed", type=int, default=42, help="抽样随机种子（默认 42）")
    parser.add_argument(
        "--out",
        type=str,
        default=str(EVAL_DIR / "testset.jsonl"),
        help="输出路径（默认 eval_data/testset.jsonl）",
    )
    args = parser.parse_args()

    print("[1/4] 加载结构化 JSON ...")
    characters = _load_json("characters.json")
    ranks = _load_json("character_ranks.json")
    skills = _load_json("character_skills.json")

    print("[2/4] 按模板生成问题 ...")
    md_roles = _md_role_names()
    samples = build_rank_questions(characters, ranks, md_roles)
    samples += build_skill_questions(characters, skills, md_roles)
    print(f"      生成 {len(samples)} 条（星魂 {sum(1 for s in samples if s['type']=='rank')} / "
          f"技能 {sum(1 for s in samples if s['type']=='skill')}，覆盖 {len(md_roles)} 个角色 md）")

    if args.size and args.size > 0 and args.size < len(samples):
        rng = random.Random(args.seed)
        samples = rng.sample(samples, args.size)
        print(f"[3/4] 按 seed={args.seed} 抽样 {args.size} 条")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"[4/4] 已写入 {len(samples)} 条 -> {out_path}")


if __name__ == "__main__":
    main()
