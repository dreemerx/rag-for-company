# 🤖 企业 RAG 智能助手

面向企业内部员工的 RAG 智能代理系统，支持知识库检索、业务数据查询、工单管理、邮件摘要、审批处理等功能。

## ✨ 功能特性

### 核心功能
- 🔐 **用户认证** - JWT + RBAC 权限管理，预留 SSO 适配器接口
- 📚 **知识库检索** - 支持 PDF、Word、Markdown、TXT 多格式文档导入
- 📊 **数据库查询** - 查询业务数据，生成报表
- 📋 **工单管理** - 对接 Jira、飞书项目等
- 📧 **邮件摘要** - 读取未读邮件，生成摘要
- ✅ **审批处理** - 查看/发起/处理审批

### 权限管理
- **普通用户** - 知识库检索、数据查询、工单、邮件、审批查询
- **管理层** - 团队概览、审批流处理
- **管理员** - 系统管理、用户管理、评测

### 技术特性
- 🔄 **LLM 可切换** - 支持云端 MiMo 和本地 Qwen 切换
- 🛡️ **高风险确认** - 审批等高风险操作需用户确认
- 🔁 **自动重试** - 工具调用失败自动重试（最多2次，指数退避）
- 📉 **降级兜底** - 重试失败自动切换备用工具
- ⚡ **限流保护** - 单用户每分钟请求限制 + Token 上限
- 📏 **自动评测** - 内置评测集，支持准确率检查

## 🛠️ 技术栈

| 组件 | 技术选型 |
|------|----------|
| Agent 框架 | LlamaIndex |
| 向量数据库 | Chroma |
| 云端 LLM | 小米 MiMo |
| 本地 LLM | 千问 Qwen |
| 后端框架 | FastAPI |
| 前端框架 | React + Ant Design |
| 认证 | JWT + RBAC |
| 部署 | Docker |

## 🚀 快速开始

### 1. 环境准备

- Python 3.11+
- Node.js 18+
- Docker (可选)

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

### 3. 后端启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m backend.main
```

### 4. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 5. Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📁 项目结构

```
rag-for-company/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config/              # 配置管理
│   ├── auth/                # 认证模块
│   ├── agent/               # Agent 核心
│   ├── tools/               # 工具系统
│   ├── knowledge/           # 知识库管理
│   ├── chat/                # 对话管理
│   └── evaluation/          # 评测模块
├── frontend/
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── api/             # API 请求
│   │   └── store/           # 状态管理
│   └── package.json
├── tests/                   # 测试文件
├── docker-compose.yml
└── .env.example
```

## 📖 API 文档

启动后端后访问：http://localhost:8000/docs

### 主要接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/chat/send` | POST | 发送消息 |
| `/api/v1/chat/ws/{token}` | WS | WebSocket 对话 |
| `/api/v1/knowledge/upload` | POST | 上传文档 |
| `/api/v1/evaluation/run` | POST | 运行评测 |

## 🔧 配置说明

### LLM 切换

在 `.env` 中设置：

```bash
# 使用云端 MiMo
LLM_PROVIDER=cloud
MIMO_API_KEY=your-api-key
MIMO_API_BASE=https://api.mimo.com/v1

# 使用本地 Qwen
LLM_PROVIDER=local
LOCAL_MODEL_PORT=8000
```

### 限流配置

```bash
RATE_LIMIT_PER_MINUTE=20      # 每分钟最多请求次数
TOKEN_LIMIT_PER_SESSION=50000 # 单次会话 Token 上限
```

## 🧪 测试

```bash
# 运行测试
pytest tests/ -v

# 运行评测
curl -X POST http://localhost:8000/api/v1/evaluation/run \
  -H "Authorization: Bearer your-admin-token"
```

## 📝 开发计划

- [ ] WebSocket 流式输出
- [ ] 飞书/企业微信 SSO 对接
- [ ] 更多工具集成
- [ ] 对话历史持久化
- [ ] 知识库增量更新
- [ ] 多轮对话优化

## 📄 License

MIT License
