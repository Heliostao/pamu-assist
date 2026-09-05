# 垂直领域知识问答助手——帕姆帮帮

基于 Agentic RAG 的崩坏:星穹铁道知识助手。登录后向列车长帕姆提问，即可获得游戏角色、机制、术语相关的流式回答。

## 快速访问

在线体验：http://115.29.187.138:426

## 版本更新

> **V2.4（当前）** — 新增 RAG 评估与 RAG 查询优化：
> - 支持口语化问答与一次性问多个问题，减少无效检索、提升答案相关性
> - 检索与优化工具统一交由 ToolNode 执行，收敛手写执行逻辑，链路更清晰
> - 新增离线 RAG 评估

> **V2.3** — 短期记忆与登录/对话交互优化：
> - 新增短期记忆：帕姆可在单个对话内记住上下文，支持"她/他"等指代与连续追问
> - 优化登录问题：服务重启后旧登录态自动失效，重新进入需重新登录
> - 修复连续点击"新建对话"会创建多个空会话的 bug（后端幂等 + 前端守卫）
> - 新增删除对话确认弹窗与"已是最新对话"提示弹窗

> **V2.2** — 登录流程优化与角色检索修复：
> - 优化登录流程：新增账号注册功能，注册即绑定邮箱，注册时新增展示用户名
> - 修复网页端未能检索到角色知识的 bug

> **V2.1** — 移动端适配与侧边栏交互优化：
> - 修复移动端登录后对话界面排版错乱问题，消息区、输入区自适应屏幕宽度
> - 侧边栏新增展开/收起按钮：桌面端可收起让出空间，移动端为抽屉式滑出，点击遮罩关闭

> **V2.0** — 新增登录界面与历史对话：
> - 新增登录界面：账号密码登录 + 邮箱验证码登录（未注册邮箱自动注册）
> - 新增历史对话：侧边栏会话列表，支持新建 / 切换 / 删除会话

> **V1.1** — 修复回答重复输出；Chroma 知识库内嵌进项目。

> **V1.0** — 首版：Agentic RAG 角色知识助手。

## 效果展示

登录界面

![登录界面](images/登录界面.png)

聊天界面

![聊天界面](images/聊天界面.png)

IR评估
![评估指标.png](images/%E8%AF%84%E4%BC%B0%E6%8C%87%E6%A0%87.png)


## 核心特性

- **Agentic RAG**：LLM 自主判断是否需要检索，检索结果经相关性评估后再生成，不相关时兜底回答，降低幻觉
- **查询优化**：口语化、带指代的提问自动改写（rewrite）为规范检索词；一次问多个独立子问题时自动拆分（split）、分别检索后合并，减少无效检索
- **帕姆人设**：全程以列车长帕姆的口吻应答
- **流式输出**：SSE 逐字推送，首字即出
- **短期记忆**：单对话内携带最近多轮上下文，支持指代词与连续追问
- **RAG 评估**：离线测试集跑 MRR / Recall@K / Precision@K / nDCG@K 并输出雷达图；在线检索日志自动落盘供复盘
- **账号体系**：账号密码 / 邮箱验证码双登录，JWT 鉴权，历史会话按用户隔离

## 系统架构

```mermaid
graph TB
    subgraph 前端
        U[浏览器 · Vue3 登录页/对话页]
    end

    subgraph 服务层
        U -->|REST /auth /conversations| API[FastAPI]
        U -->|SSE /chat| API
        API -->|Bearer JWT| AUTH[JWT + bcrypt 认证]
    end

    subgraph Agent 层
        API -->|astream| LG[LangGraph]
        LG --> CH[chatbot 节点<br/>LLM 决策 + 工具调用]
        CH -->|无 tool_call| E1((结束·直接回复))
        CH -->|tool_call| TN[ToolNode 统一执行]
        TN -->|retrieve_knowledge| FMT[format 节点<br/>解析检索结果]
        TN -->|optimize_plan| OPT[optimize 节点<br/>rewrite / split + 检索]
        FMT --> GD[grade 节点<br/>相关性评估 → 生成/兜底]
        OPT --> GD
        GD --> E2((结束))
    end

    subgraph 检索管线
        VS[(Chroma 向量库)] -->|BGE 向量召回 top10| RR[bge-reranker 精排 top3]
        FMT -.-> VS
        OPT -.-> VS
        RR -.->|Redis 缓存命中<br/>跳过召回与重排| RD2[(Redis 检索缓存)]
    end

    subgraph 存储层
        AUTH --> RD[(Redis 验证码)]
        API --> PG[(PostgreSQL<br/>用户 / 会话 / 消息)]
        CH --> DS[DeepSeek API]
    end
```

工作流：LLM 决策 →（需要时）工具执行。常规问题走 `retrieve_knowledge`：向量召回 top 10 → CrossEncoder 重排 top 3，结果缓存 Redis；口语化 / 一次多问题走 `optimize_plan` 查询优化：rewrite 结合多轮历史改写查询词，split 拆出子问题分别召回后合并重排 → grade 节点相关性评估 → 生成帕姆风格回答；无工具调用或检索不相关时直接回答 / 兜底。

## 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| 前端 | Vue3 + Vite | 组件化登录页/对话页，构建产物由后端托管，单端口部署 |
| 后端 | FastAPI | 异步接口 + SSE 流式，静态文件托管 |
| Agent 框架 | LangGraph | 显式状态图，节点可观测、条件分支可控 |
| 认证 | JWT + bcrypt | 无状态鉴权，密码哈希存储 |
| 验证码 | SMTP + Redis | QQ 邮箱发信，Redis 存码（5 分钟过期 + 60s 冷却） |
| 业务存储 | PostgreSQL | 用户、会话、消息持久化 |
| 向量库 | Chroma（持久化） | 嵌入式运行，无需独立服务 |
| Embedding / 重排 | BGE base-zh / reranker | 中文语义本地推理，零调用成本 |
| 大模型 | DeepSeek | 中文能力强、支持 function calling |

## 项目结构

```
pamu_assist/
├── main.py                  # FastAPI 入口：/chat SSE、静态托管、启动初始化
├── frontend/                # Vue3 + Vite 前端工程（构建输出到 src/static）
├── src/
│   ├── api/                 # REST 接口：auth（认证）、conversations（会话）
│   ├── auth/                # JWT/bcrypt、SMTP 发信、Redis 验证码
│   ├── database/            # SQLAlchemy 模型 + PostgreSQL
│   ├── graph/               # LangGraph 工作流：chatbot / tools / format / optimize / grade 节点 + 路由
│   ├── models/              # DeepSeek LLM、Chroma + BGE
│   ├── tools/               # 检索工具 retrieve_knowledge、查询优化工具 optimize_plan
│   ├── retriever/           # 向量召回（vector）+ 压缩检索（召回→重排组装）
│   ├── reranker/            # bge-reranker CrossEncoder 精排
│   ├── prompts/             # 帕姆人设 / 相关性评估 / 查询改写 / 问题拆分 Prompt
│   ├── data_loader/         # 知识入库（加载/切分/索引）
│   ├── util/                # .env 配置
│   └── static/              # 前端构建产物
├── scripts/                 # 离线评估：gen_testset（生成测试集）、eval_ragas（IR 指标 + 雷达图）
├── eval_data/               # 测试集与在线检索日志
├── data/                    # Wiki 原始数据
├── chroma_data/             # Chroma 持久化向量库
├── crawler/                 # Wiki JSON → Markdown
└── Dockerfile               # 多阶段构建（Node 构建前端 + Python 运行）
```

## 快速开始

环境要求：Python 3.10+、Node 20+（仅构建前端需要）、PostgreSQL、Redis、DeepSeek API Key。

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 构建前端
cd frontend && npm install && npm run build && cd ..

# 3. 配置 .env（键参考：DEEPSEEK_API_KEY / SECRET_KEY / SMTP_* / REDIS_* /
#    DATABASE_URL=postgresql+psycopg2://pamu:pamu@localhost:5433/pamu / DEFAULT_USERNAME / DEFAULT_PASSWORD）

# 4. 启动 PostgreSQL 与 Redis，然后启动服务
python main.py
# 访问 http://localhost:426/
```

也可用 Docker 一键部署（需外部 PostgreSQL/Redis 可达）：`docker build -t pamu-assist . && docker run -p 426:426 --env-file .env pamu-assist`

## 接口一览

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/auth/vcode` | 发送邮箱验证码 | - |
| POST | `/auth/login/email` | 邮箱验证码登录（自动注册） | - |
| POST | `/auth/login/password` | 账号密码登录 | - |
| GET | `/auth/me` | 当前用户信息 | Bearer |
| GET/POST | `/conversations` | 会话列表 / 新建 | Bearer |
| DELETE | `/conversations/{id}` | 删除会话 | Bearer |
| GET | `/conversations/{id}/messages` | 会话消息 | Bearer |
| POST | `/chat` | SSE 流式对话（自动记录问答） | Bearer |
