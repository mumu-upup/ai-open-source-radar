# 动态教案平台第一阶段设计

> 版本：v0.1  
> 日期：2026-09-27  
> 范围：独立的 `dynamic-lesson-platform` Java 后端最小闭环

## 1. 目标

建立一个可被 IntelliJ IDEA 直接打开、可测试、可扩展的动态教案生成后端。用户提交学科、年级、课时、教材内容和学情后，系统生成结构化教案；每次模型或模拟模型调用都记录资源用量，为后续按 Token、图片、音频和存储计费提供稳定接口。

本阶段不实现完整的 Web 前端、支付渠道、生产级登录和真实模型密钥接入。真实模型接入通过接口预留，避免供应商 SDK 渗透到业务层。

## 2. 非目标

- 不修改或迁移已有 `manju-platform` 漫剧项目。
- 不复制 LearnHouse、BoxyHQ 或其他 AGPL 项目的源代码。
- 不在代码中保存 OpenAI、Claude、Gemini、通义、DeepSeek、智谱等供应商密钥。
- 不把平台积分、真实 Token 和支付流水混成一个字段。
- 不在第一版实现异步队列、对象存储、在线协作编辑器和支付回调。

## 3. 技术方案

| 层次 | 选择 | 说明 |
| --- | --- | --- |
| 语言 | Java 17 | 与 IntelliJ IDEA 和 Spring Boot 3.3 兼容 |
| Web | Spring Boot 3.3.x、Spring MVC、Bean Validation | 提供 REST API 和请求校验 |
| 构建 | Maven Wrapper | 新环境无需预装 Maven |
| 领域结构 | Controller / Application / Domain / Infrastructure | 保持模型网关和计量边界清晰 |
| 持久化 | 第一阶段内存实现，接口预留 PostgreSQL | 便于先验证业务契约 |
| 测试 | JUnit 5、Spring Boot Test | 服务单测与 Controller 集成测试 |
| 规范 | 阿里 Java 开发手册风格 | 中文 Javadoc、明确异常、禁止魔法值、构造器注入 |

## 4. 模块设计

### 4.1 生成模块

`LessonGenerationController` 接收 `LessonGenerationRequest`，调用 `LessonGenerationApplicationService` 完成以下流程：

1. 校验并规范化请求。
2. 调用 `ModelGateway` 生成结构化教学设计。
3. 校验教案必须包含目标、重点难点、教学环节和评价方式。
4. 记录本次模型调用的输入 Token、输出 Token、模型标识和状态。
5. 返回 `LessonGenerationResult`，包括教案、生成任务标识和用量摘要。

第一阶段使用 `DeterministicLessonModelGateway`，让本地开发和测试可重复；真实供应商适配器以后只实现 `ModelGateway`，不改变 Controller、领域对象或计量服务。

### 4.2 用量模块

`UsageMeteringService` 接收不可变的 `UsageEvent`，记录：

- 工作空间标识；
- 用户标识；
- 任务标识；
- 资源类型（TEXT_TOKEN、IMAGE、AUDIO_SECOND、STORAGE_BYTE）；
- 输入数量、输出数量、模型标识和供应商标识；
- 事件时间和幂等键。

计费金额不在生成服务中计算。`UsagePricingService` 根据可配置的价格表计算预估费用，返回平台积分和原始资源量，后续可替换为 OpenMeter 或数据库实现。

### 4.3 模型网关模块

`ModelGateway` 使用结构化输入输出：

```java
ModelGenerationResponse generate(ModelGenerationRequest request);
```

响应必须包含 `LessonPlan` 和 `ModelUsage`。模型名称、供应商、能力类型和价格均为配置数据，业务代码不能写死供应商 SDK 类型。

### 4.4 文档模块

每个大模块沉淀独立文档：

- `docs/architecture.md`：分层和依赖方向；
- `docs/lesson-generation-workflow.md`：动态教案生成流程和结构化数据；
- `docs/usage-metering.md`：用量事件、幂等和计费边界；
- `docs/local-development.md`：IDEA 导入、测试和配置方式。

## 5. 数据流

```text
HTTP 请求
   ↓
请求校验与规范化
   ↓
LessonGenerationApplicationService
   ├── ModelGateway
   ├── LessonPlanValidator
   └── UsageMeteringService
   ↓
结构化教案 + 用量摘要
```

## 6. API 契约

### 6.1 生成教案

`POST /api/v1/lessons/generations`

请求示例：

```json
{
  "workspaceId": "workspace-demo",
  "userId": "teacher-demo",
  "subject": "数学",
  "grade": "八年级",
  "topic": "一次函数的图像与性质",
  "durationMinutes": 45,
  "studentProfile": "基础差异较大，需要分层练习",
  "sourceMaterial": "教材第三章一次函数"
}
```

返回值包括 `generationId`、结构化 `lessonPlan`、`usageSummary` 和 `status`。

### 6.2 查询用量

`GET /api/v1/workspaces/{workspaceId}/usage`

返回当前工作空间按资源类型聚合的消耗，以及按当前价格表计算的预估平台积分。没有数据时返回零值，不返回空集合或 `null`。

### 6.3 健康检查

`GET /api/v1/health`

返回服务状态和版本信息，供 IDEA 本地启动和后续部署探活使用。

## 7. 错误处理

- 请求参数不合法返回 HTTP 400 和字段级中文错误信息。
- 模型网关失败返回 HTTP 502，保留任务标识和失败用量事件，不覆盖已有教案。
- 用量记录失败时生成任务失败，避免出现“生成成功但无法计费”的账务不一致。
- 业务异常使用统一响应结构，禁止把堆栈信息返回给客户端。
- 所有事件写入使用幂等键，重复请求不会重复扣量。

## 8. 测试策略

- 领域单元测试：请求规范化、教案结构校验、用量聚合和价格计算。
- 应用服务测试：模型成功、模型失败、用量记录失败和重复幂等键。
- Controller 测试：成功响应、参数校验错误和异常映射。
- 每一个生产类新增或修改必须先新增失败测试，再实现最小代码。

## 9. 交付与仓库

- 项目目录：`dynamic-lesson-platform/`；
- GitHub 仓库：创建为 Private；
- 默认分支：`main`；
- `.gitignore` 排除 IDE 配置、构建产物、本地密钥和环境配置；
- 提交前运行 `./mvnw test`；
- GitHub CLI 当前不可用，因此推送前需要用户在浏览器或 Git 凭据管理器完成授权；不会把代码推送到公开仓库。

