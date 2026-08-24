# 帕姆帮帮 · 崩坏:星穹铁道 AI 助手（V2.3）

基于 Agentic RAG 的崩坏:星穹铁道知识助手。登录后向列车长帕姆提问，即可获得游戏角色、机制、术语相关的流式回答。

## 快速访问

在线体验：http://115.29.187.138:426

## 版本更新

> **V2.3（当前）** — 短期记忆与登录/对话交互优化：
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
> - 前端重构为 Vue3 + Vite 工程（替代原单文件页面），构建产物由 FastAPI 统一托管
> - 新增认证与存储层：JWT + bcrypt 认证，PostgreSQL 持久化用户/会话/消息，Redis 存储验证码

> **V1.1** — 修复回答重复输出；Chroma 知识库内嵌进项目。

> **V1.0** — 首版：Agentic RAG 角色知识助手。

## 效果展示

登录界面

![登录界面](images/登录界面.png)

聊天界面

![聊天界面](images/聊天界面.png)




## 核心特性

- **Agentic RAG**：LLM 自主判断是否需要检索，检索结果经相关性评估后再生成，不相关时兜底回答，降低幻觉
- **帕姆人设**：全程以列车长帕姆的口吻应答
- **流式输出**：SSE 逐字推送，首字即出
- **短期记忆**：单对话内携带最近多轮上下文，支持指代词与连续追问
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
        CH -->|tool_call| TN[ToolNode 检索]
        TN --> GD[grade 节点<br/>相关性评估 → 生成/兜底]
    end

    subgraph 检索管线
        TN --> VS[(Chroma 向量库)]
        VS -.-> BGE[BGE embedding + reranker 本地模型]
    end

    subgraph 存储层
        AUTH --> RD[(Redis 验证码)]
        API --> PG[(PostgreSQL<br/>用户 / 会话 / 消息)]
        CH --> DS[DeepSeek API]
    end
```

工作流：LLM 决策 →（需要时）向量检索 top 8 + CrossEncoder 重排 top 5 → 相关性评估 → 生成帕姆风格回答；无工具调用或检索不相关时直接回答 / 兜底。

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
│   ├── graph/               # LangGraph Agentic RAG 工作流
│   ├── models/              # DeepSeek LLM、Chroma + BGE
│   ├── tools/               # 检索工具（向量检索 + 重排）
│   ├── prompts/             # 帕姆人设 / 相关性评估 Prompt
│   ├── data_loader/         # 知识入库（加载/切分/索引）
│   ├── util/                # .env 配置
│   └── static/              # 前端构建产物
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
