# Game Chat

一个面向游戏场景的 AI 陪玩系统，为用户提供角色化陪伴、游戏知识问答、连续对话和语音交互能力。

## 项目简介

用户登录后可以选择陪玩角色、游戏和聊天会话。系统根据当前会话状态加载短期记忆、长期记忆以及对应游戏知识库，让 AI 在保持角色风格的同时，为用户提供自然的陪伴和游戏交流体验。
对于chrome扩展的演示在b站：https://b23.tv/RrxALhj

## 主要功能

- 用户注册与登录
- 陪玩角色选择与切换
- 游戏模式与纯聊天模式
- 多会话创建、切换和历史记录查看
- 短期记忆与长期记忆总结
- 基于游戏知识库的 RAG 检索
- LangGraph 工作流管理
- AI 回复流式输出
- 语音输入与语音播报
- Electron 悬浮窗模式
- Neo4j 用户、角色和会话关系同步实验

## 技术栈

### 后端

- Python
- FastAPI
- SQLAlchemy
- MySQL
- LangChain
- LangGraph
- Neo4j
- RAG
- OpenAI 兼容模型接口
- 阿里云 DashScope Qwen ASR/TTS

### 前端

- Vue 3
- TypeScript
- Vite
- Electron

## 项目结构

```text
game_chat/
├── backend/       # FastAPI 接口、数据库模型和语音服务
├── frontend/      # Vue 前端和 Electron 悬浮窗
├── workflow/      # LangGraph 工作流
├── rag/           # 知识库加载、切分、检索和格式化
├── knowledge/     # 游戏知识库文件
├── prompts/       # 陪玩角色提示词
├── memory.py      # 短期记忆和长期记忆管理
├── llm.py         # 大语言模型调用
├── role_loader.py # 角色和游戏名称映射
└── config.py      # 项目配置
```

## 运行方式

### 1. 克隆项目

请先安装 Git、Anaconda 或 Miniconda、Node.js 和 MySQL，然后执行：

```bash
git clone https://github.com/namedsi872-cmd/game_chat.git
cd game_chat
```

### 2. 创建并安装 Python 环境

项目基于 Python 3.10 开发。使用 Conda 创建独立环境并一键安装后端依赖：

```bash
conda create -n multi_agent python=3.10 -y
conda activate multi_agent
pip install -r requirements.txt
```

首次安装 `faster-whisper` 会下载语音识别所需模型文件，耗时取决于网络环境。

### 3. 配置本地参数

在项目根目录创建 `.env`，填入自己的模型接口、MySQL 和 DashScope 参数。`.env` 包含密钥和密码，不应提交到 GitHub。

### 4. 启动后端

```bash
uvicorn backend.app:app --reload --port 8000
```

后端接口文档地址：

```text
http://127.0.0.1:8000/docs
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 6. 启动 Electron 悬浮窗

```bash
cd frontend
npm run electron
```

## 记忆系统

系统使用 MySQL 保存用户、会话、聊天消息和长期记忆。

- 短期记忆：保存当前会话中的近期消息
- 长期记忆：短期消息达到指定数量后，由模型生成总结并保存
- 会话记忆：不同角色、游戏和会话之间相互隔离

## RAG 知识库

游戏资料按照游戏名称分类保存：

```text
knowledge/
└── dwrg/
    └── raw/
        ├── character_intro.md
        └── dentist_training.md
```

系统会根据当前会话绑定的游戏，从对应知识库中检索相关内容，再交给模型生成回答。

## 工作流

系统使用 LangGraph 组织消息处理流程。当前流程会接收用户、角色、会话和游戏信息，判断当前请求类型，加载对应的短期记忆和长期记忆，再交给聊天或训练流程处理。

## Neo4j

项目保留了 Neo4j 用户、角色和会话关系同步的实验代码，目前尚未作为正式聊天链路的一部分。

## 安全说明

API Key、数据库密码和 Neo4j 密码均应通过环境变量配置，不应直接写入源代码或提交到公开仓库。
