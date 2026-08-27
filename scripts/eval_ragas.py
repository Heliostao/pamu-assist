"""
传统 IR 指标评估（纯计算，零 LLM 成本）。

读取 eval_data/testset.jsonl（模板生成，含 question/ground_truth/target_role），
调用现有检索链路（Chroma 向量召回 + bge-reranker 精排，即 rag_tool 的
_compression_retriever），对每条问题取 top K 检索结果，计算：

- MRR          ：第一个命中相关 chunk 的排位倒数
- Recall@K     ：Top K 中命中相关 chunk / 总相关 chunk（此处按"应命中的 chunk"=1 计）
- Precision@K  ：Top K 中命中相关 chunk / K
- nDCG@K       ：按排序位置的折扣累计增益

命中判断（防跨角色误判的双保险）：
1. 检索 chunk 的 content 包含 ground_truth 文本（星魂 desc / 技能 simple_desc，
   均与 md 原文逐字一致）；
2. 检索 chunk 的 source 文件名包含 target_role（如 "data/character/黄泉.md"）。

注意：检索链路依赖 Docker 中的 Chroma，评估前需保证 pamu-chroma 容器已启动。
"""
import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.rag_tool import _compression_retriever  # noqa: E402
from src.util.config import PROJECT_ROOT as CFG_ROOT  # noqa: E402
from src.util.config import RERANK_TOP_N  # noqa: E402

DEFAULT_EVAL_DIR = Path(CFG_ROOT) / "eval_data"


# ---------- 指标计算 ----------

def _dcg(ranks: list[int], k: int) -> float:
    """折扣累计增益：ranks 中元素为命中的排位（1-based）。"""
    gain = 0.0
    for r in ranks:
        if r <= k:
            gain += 1.0 / math.log2(r + 1)
    return gain


def _idcg(k: int) -> float:
    """理想 DCG：前 k 位全部命中。"""
    return sum(1.0 / math.log2(i + 1) for i in range(1, k + 1))


def compute_metrics(hit_positions: list[int], k: int) -> dict:
    """由命中排位列表（1-based，可为空）计算四项指标。"""
    first_hit = hit_positions[0] if hit_positions else None
    return {
        "mrr": 1.0 / first_hit if first_hit else 0.0,
        f"recall@{k}": 1.0 if first_hit else 0.0,  # 每条样本应命中 1 个相关 chunk
        f"precision@{k}": (1.0 / k if first_hit else 0.0),
        f"ndcg@{k}": _dcg(hit_positions, k) / _idcg(k) if hit_positions else 0.0,
    }


def _doc_content(doc) -> str:
    """兼容 dict 与 langchain Document 两种检索结果形态。"""
    if isinstance(doc, dict):
        return (doc.get("content") or doc.get("page_content") or "").strip()
    return (getattr(doc, "page_content", None) or "").strip()


def _doc_source(doc) -> str:
    """取检索结果的 source（dict 的 source 键 / Document 的 metadata.source）。"""
    if isinstance(doc, dict):
        return (doc.get("source") or "").strip()
    meta = getattr(doc, "metadata", None) or {}
    return (meta.get("source") or "").strip()


def is_hit(doc, target_role: str, ground_truth: str) -> bool:
    """命中判断：content 包含 ground_truth 且 source 文件名含 target_role。"""
    content = _doc_content(doc)
    source = _doc_source(doc)
    if not content or not ground_truth.strip():
        return False
    if ground_truth.strip() not in content:
        return False
    # source 可能是 "data/character/黄泉.md" 或纯文件名 "黄泉.md"
    if target_role not in Path(source).name and target_role not in source:
        return False
    return True


# ---------- 主流程 ----------

def draw_radar_chart(metrics: dict, save_path: Path, k: int) -> None:
    """绘制并保存雷达图（4 轴，按各轴理论上限归一化为达成率）。

    各轴理论上限（当前"每题仅 1 个相关文档"的评估口径下的数学上限）：
    - MRR / Recall@K / nDCG@K: 1.0
    - Precision@K: 1/K（top-K 最多命中 1 个相关文档）
    图形显示的是 实际值/理论上限 的达成率，四轴共用 0~100% 刻度，
    顶点标注原始值与达成率，避免 Precision 因上限仅 0.2 被压缩成短线。
    """
    # 中文字体兜底
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    limits = {
        "mrr": 1.0,
        f"recall@{k}": 1.0,
        f"precision@{k}": 1.0 / k,
        f"ndcg@{k}": 1.0,
    }
    keys = ["mrr", f"recall@{k}", f"precision@{k}", f"ndcg@{k}"]
    labels = [
        "MRR\n平均倒数排名\n上限 1.0",
        f"Recall@{k}\n召回率\n上限 1.0",
        f"Precision@{k}\n精确率\n上限 {1/k:.1f}",
        f"nDCG@{k}\n归一化折损累计增益\n上限 1.0",
    ]
    raw_values = [metrics[key] for key in keys]
    # 达成率 = 实际值 / 理论上限，钳制在 [0, 1]
    rates = [min(v / limits[key], 1.0) for v, key in zip(raw_values, keys)]

    # 角度：第一个标签在正上方（matplotlib 0° 在右侧，偏移 +90°）
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles = [a + np.pi / 2 for a in angles]

    # 闭合图形
    plot_angles = angles + angles[:1]
    plot_rates = rates + rates[:1]

    fig, ax = plt.subplots(figsize=(8.5, 8.5), subplot_kw=dict(polar=True))
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"], color="grey", size=10)

    # 绘制边框与填充
    ax.plot(plot_angles, plot_rates, color="#E74C3C", linewidth=2)
    ax.fill(plot_angles, plot_rates, color="#E74C3C", alpha=0.25)

    # 轴标签（英文 + 中文 + 上限，pad 外移避免与图形重叠）
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, size=10.5)
    ax.tick_params(axis="x", pad=16)

    # 在每个顶点外侧标注：原始值（达成率）
    for angle, raw, rate in zip(angles, raw_values, rates):
        ax.text(
            angle,
            rate + 0.09,
            f"{raw:.3f}（{rate:.0%}）",
            ha="center",
            va="center",
            color="#C0392B",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title("帕姆帮帮 IR评估", size=16, pad=22)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"雷达图已保存: {save_path}")


def load_testset(path: Path) -> list[dict]:
    samples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="传统 IR 指标评估（MRR/Recall@K/Precision@K/nDCG）")
    parser.add_argument(
        "--testset",
        type=str,
        default=str(DEFAULT_EVAL_DIR / "testset.jsonl"),
        help="测试集路径（默认 eval_data/testset.jsonl）",
    )
    parser.add_argument(
        "--top-k", type=int, default=RERANK_TOP_N, help=f"评估的 K 值（默认取 RERANK_TOP_N={RERANK_TOP_N}）"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="只评估前 N 条（0=全部），用于快速试跑"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="雷达图保存路径（默认 eval_data/radar_k{K}.png）",
    )
    args = parser.parse_args()

    testset_path = Path(args.testset)
    if not testset_path.exists():
        print(f"测试集不存在: {testset_path}（先运行 scripts/gen_testset.py 生成）")
        sys.exit(1)

    samples = load_testset(testset_path)
    if args.limit and args.limit > 0:
        samples = samples[: args.limit]
    print(f"加载测试集 {len(samples)} 条 <- {testset_path}")

    # 累计指标
    sums = {k: 0.0 for k in ["mrr", f"recall@{args.top_k}", f"precision@{args.top_k}", f"ndcg@{args.top_k}"]}
    n_miss = 0  # 完全未命中的条数

    for i, sample in enumerate(samples, 1):
        question = sample.get("question", "")
        target_role = sample.get("target_role", "")
        ground_truth = sample.get("ground_truth", "")

        try:
            docs = _compression_retriever.invoke(question)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(samples)}] 检索失败，跳过: {question[:30]}... ({exc})")
            continue

        hit_positions = [
            idx + 1 for idx, doc in enumerate(docs[: args.top_k]) if is_hit(doc, target_role, ground_truth)
        ]
        metrics = compute_metrics(hit_positions, args.top_k)
        for key in sums:
            sums[key] += metrics[key]
        if not hit_positions:
            n_miss += 1
        if i % 20 == 0 or i == len(samples):
            print(f"  进度 {i}/{len(samples)}，当前 MRR={sums['mrr'] / i:.4f}")

    n = len(samples)
    if n == 0:
        print("无有效样本")
        sys.exit(1)

    print("\n===== 传统 IR 评估结果 =====")
    final_metrics: dict[str, float] = {}
    for key, total in sums.items():
        val = total / n
        final_metrics[key] = val
        print(f"  {key}: {val:.4f}")
    print(f"  未命中条数: {n_miss}/{n}（{n_miss / n * 100:.1f}%）")

    # 生成雷达图
    out_path = Path(args.output) if args.output else DEFAULT_EVAL_DIR / f"radar_k{args.top_k}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    draw_radar_chart(final_metrics, out_path, args.top_k)


if __name__ == "__main__":
    main()
