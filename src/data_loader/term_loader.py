"""
术语表加载器 — 解析崩坏星穹铁道术语表并生成 LangChain Document
"""
from pathlib import Path
from langchain_core.documents import Document

# 章节 → 细粒度 doc_type 映射
SECTION_TYPE_MAP: dict[str, str] = {
    "一、基础信息": "术语 基础信息相关",
    "二、9 种命途": "术语 命途相关",
    "三、7种战斗属性": "术语 战斗属性相关",
    "四、技能类型": "术语 技能类型相关",
    "五、技能范围 / 效果标签": "术语 技能效果相关",
    "六、星魂": "术语 星魂相关",
    "七、行迹": "术语 行迹相关",
    "八、核心战斗属性": "术语 核心属性相关",
    "九、伤害与机制通用术语": "术语 机制相关",
    "十、欢愉体系特殊术语": "术语 欢愉体系相关",
}


def load_term_documents(term_dir: str) -> list[Document]:
    """读取术语表，按条目逐行拆分为 Document。

    每行格式：术语名 — 描述
    例：稀有度 — 角色品质，四星或五星
    """
    term_path = Path(term_dir)
    docs: list[Document] = []
    current_section = ""

    for txt_path in term_path.glob("*.txt"):
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()

            # 跳过空行、分隔线、标题
            if not line or line.startswith("━") or line == "崩坏：星穹铁道角色术语整理":
                continue

            # 记录当前章节（一、二、三...）
            if line.startswith(("一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、")):
                current_section = line
                continue

            # 解析 "术语名 — 描述" 条目
            if " — " in line:
                term, desc = line.split(" — ", 1)
                content = f"【{term}】{desc}"
                doc_type = SECTION_TYPE_MAP.get(current_section, "术语 其他相关")
                docs.append(Document(
                    page_content=content,
                    metadata={
                        "source": txt_path.name,
                        "term": term,
                        "doc_type": doc_type,
                    },
                ))

    return docs
