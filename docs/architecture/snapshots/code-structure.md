# 当前代码结构快照

本文件记录当前仓库已经拉取到本地并纳入版本管理的实际代码结构，供后续智能体和开发协作时参考。

当前项目采用前后端单仓：后端以 `app/` 为模块化单体根目录，没有额外的 `backend/` 包装目录；Web 客户端位于 `frontend/`；Android 客户端位于 `android/`。项目文档集中在 `docs/`，多智能体协作专题文档归档在 `docs/architecture/multi-agent-collaboration.md`。

请不要轻易调整现有文件结构，如需修改，请先和用户沟通，不要擅自修改。如果已经确认要更改文件结构，请及时更新本快照。

```text
.
├── .agent/
│   ├── architecture.md
│   ├── conventions.md
│   ├── decisions.md
│   └── guardrails.md
├── .dockerignore
├── .env.example
├── .gitignore
├── .gitlab-ci.yml
├── Dockerfile
├── pytest.ini
├── README.md
├── android/
│   ├── .gitignore
│   ├── build.gradle.kts
│   ├── gradle.properties
│   ├── gradlew / gradlew.bat
│   ├── settings.gradle.kts
│   └── app/
│       ├── build.gradle.kts
│       └── src/main/
│           ├── AndroidManifest.xml
│           └── java/com/travel/planner/
│               ├── App.kt
│               ├── MainActivity.kt
│               ├── data/
│               │   ├── local/datastore/TokenStore.kt
│               │   ├── remote/
│               │   │   ├── api/ (AuthApi, PlanApi, TripApi, TravelogueApi)
│               │   │   ├── dto/Requests.kt
│               │   │   ├── interceptor/AuthInterceptor.kt
│               │   │   └── sse/SseClient.kt
│               │   └── repository/ (5 Repository Impl)
│               ├── di/ (NetworkModule, RepositoryModule)
│               ├── domain/
│               │   ├── model/Models.kt
│               │   └── repository/Repositories.kt
│               └── presentation/
│                   ├── components/common/SharedComponents.kt
│                   ├── navigation/ (AppNavigation, Routes)
│                   ├── screens/
│                   │   ├── auth/ (LoginScreen, RegisterScreen)
│                   │   ├── chat/ChatScreen.kt
│                   │   ├── home/HomeScreen.kt
│                   │   ├── plan/ (PlanListScreen, PlanDetailScreen)
│                   │   ├── travelogue/ (TravelogueScreen, MaterialListScreen)
│                   │   ├── trip/ (TripExecuteScreen, CheckInScreen)
│                   │   └── ProfileScreen.kt
│                   └── theme/ (Color, Shape, Theme, Type)
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── adjust_agent.py
│   │   ├── attraction_agent.py
│   │   ├── base.py
│   │   ├── budget_agent.py
│   │   ├── context.py
│   │   ├── decision_agent.py
│   │   ├── detail_agent.py
│   │   ├── food_agent.py
│   │   ├── hotel_agent.py
│   │   ├── photo_planner_agent.py
│   │   ├── route_optimizer_agent.py
│   │   ├── souvenir_agent.py
│   │   ├── traffic_agent.py
│   │   ├── travelogue_agent.py
│   │   ├── trip_agent.py
│   │   ├── user_interaction_agent.py
│   │   ├── weather_agent.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── attraction_tools.py
│   │       ├── budget_tools.py
│   │       ├── map_tools.py
│   │       ├── tool_registry.py
│   │       └── weather_tools.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── chat.py
│   │       ├── data.py
│   │       ├── ops.py
│   │       ├── plan.py
│   │       ├── travelogue.py
│   │       ├── trip.py
│   │       └── user.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── migrations/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       ├── 20260709_01_add_conversation_plan_runs.py
│   │   │       ├── 20260710_01_add_poi_source_identity.py
│   │   │       ├── 20260710_02_add_message_metadata_and_pinned.py
│   │   │       ├── 20260710_03_harden_conversation_ordering.py
│   │   │       ├── 20260710_04_message_sequence_not_null.py
│   │   │       ├── 20260714_01_add_trip_execution_tables.py
│   │   │       ├── 20260714_02_add_plan_full_data_fields.py
│   │   │       ├── 20260715_01_add_plan_saved_at.py
│   │   │       ├── 20260717_01_backfill_plan_result_messages.py
│   │   │       └── 20260717_02_add_travelogue_style.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── attraction.py
│   │   │   ├── base.py
│   │   │   ├── conversation.py
│   │   │   ├── hotel.py
│   │   │   ├── plan.py
│   │   │   ├── restaurant.py
│   │   │   ├── travelogue.py
│   │   │   ├── trip.py
│   │   │   └── user.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── attraction_repo.py
│   │       ├── base.py
│   │       ├── conversation_repo.py
│   │       ├── hotel_repo.py
│   │       ├── plan_repo.py
│   │       ├── restaurant_repo.py
│   │       ├── travelogue_repo.py
│   │       ├── trip_repo.py
│   │       └── user_repo.py
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── conflict_detection.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── pipeline.py
│   │   └── state.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── agent_outputs.py
│   │   ├── chat.py
│   │   ├── common.py
│   │   ├── data.py
│   │   ├── plan.py
│   │   ├── travelogue.py
│   │   ├── trip.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── conversation_service.py
│   │   │   ├── plan_service.py
│   │   │   ├── travelogue_service.py
│   │   │   ├── trip_service.py
│   │   │   └── user_service.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── attraction_service.py
│   │   │   ├── hotel_service.py
│   │   │   └── restaurant_service.py
│   │   ├── export/
│   │   │   ├── __init__.py
│   │   │   ├── exporter.py
│   │   │   └── task_manager.py
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── deepseek.py
│   │   │   ├── doubao.py
│   │   │   ├── prompt_manager.py
│   │   │   ├── qwen.py
│   │   │   └── vision.py
│   │   ├── map/
│   │   │   ├── __init__.py
│   │   │   ├── amap.py
│   │   │   └── geocode.py
│   │   ├── third_party/
│   │   │   ├── __init__.py
│   │   │   ├── meituan.py
│   │   │   ├── meituan_parser.py
│   │   │   ├── poi_live.py
│   │   │   └── railway12306.py
│   │   ├── vector/
│   │   │   ├── __init__.py
│   │   │   ├── embedding.py
│   │   │   ├── poi_index.py
│   │   │   ├── rag.py
│   │   │   ├── reranker.py
│   │   │   ├── scorer.py
│   │   │   └── vector_store.py
│   │   └── weather/
│   │       ├── __init__.py
│   │       ├── impact.py
│   │       └── qweather.py
│   └── utils/
│       ├── __init__.py
│       ├── cache.py
│       ├── logger.py
│       ├── pipeline_cache.py
│       └── validator.py
├── docs/
│   ├── README.md
│   ├── CI-CD/
│   │   └── ci-cd.md
│   ├── Sprint1/
│   │   ├── Sprint1-验收备战手册.md
│   │   ├── Sprint1AI抗性挑战完成报告_已完成.docx
│   │   ├── Sprint1质量门禁完成报告.xlsx
│   │   └── test/
│   │       ├── API响应测试数据结果.xlsx
│   │       ├── Sprint1质量门禁完成报告.xlsx
│   │       ├── Sprint1质量门禁完成报告_v2.xlsx
│   │       ├── Sprint1质量门禁完成报告_模板.xlsx
│   │       ├── api_benchmark.py
│   │       ├── api_response_benchmark.md
│   │       ├── fill_template.py
│   │       └── gen_excel.py
│   ├── Sprint2/
│   │   ├── Sprint 2 阶段验收 要求.md
│   │   ├── API响应测试数据结果.xlsx
│   │   ├── coverage-html/
│   │   ├── 代码走查-准备清单.md
│   │   ├── 性能检查-测试结果.txt
│   │   ├── 测试强化挑战-成果报告.md
│   │   ├── 边界处理-极端输入场景.md
│   │   └── 边界场景测试明细.md
│   ├── android/
│   │   └── Android客户端开发规范.md
│   ├── api/
│   │   └── API接口规范文档.md
│   ├── architecture/
│   │   ├── ARCHITECTURE.md
│   │   ├── README.md
│   │   ├── multi-agent-collaboration.md
│   │   ├── 软件架构设计文档.md
│   │   ├── 架构设计说明书.md
│   │   ├── backend/
│   │   │   ├── README.md
│   │   │   ├── 01-overall-and-data.md
│   │   │   ├── 02-rag.md
│   │   │   ├── 03-agents.md
│   │   │   ├── 04-api-and-integrations.md
│   │   │   ├── 05-code-index-and-extension.md
│   │   │   ├── 06-backend-code-explanation.md
│   │   │   └── 07-api-routes-analysis.md
│   │   ├── chapters/
│   │   │   ├── 01-概述.md
│   │   │   ├── 02-整体技术架构.md
│   │   │   ├── 03-技术选型详解.md
│   │   │   ├── 04-多智能体架构设计.md
│   │   │   ├── 05-数据架构设计.md
│   │   │   ├── 06-API接口设计.md
│   │   │   ├── 07-部署架构设计.md
│   │   │   ├── 08-安全架构设计.md
│   │   │   ├── 09-性能优化策略.md
│   │   │   ├── 10-可扩展性设计.md
│   │   │   ├── 11-开发规范与工程实践.md
│   │   │   └── 12-V2.0架构演进规划.md
│   │   ├── database/
│   │   │   └── 数据库设计文档.md
│   │   ├── diagrams/
│   │   │   ├── 01-user-journey.puml / .png
│   │   │   ├── 02-product-functions.puml / .png
│   │   │   ├── 03-agent-collaboration.puml / .png
│   │   │   └── agent-orchestration.puml / .png
│   │   ├── implementation/
│   │   │   ├── README.md
│   │   │   ├── 01-boundaries.md
│   │   │   ├── 02-data-and-integrations.md
│   │   │   └── 03-quality-and-evolution.md
│   │   └── snapshots/
│   │       └── code-structure.md
│   ├── assets/
│   ├── decisions/
│   │   ├── 01-architecture-foundation.md
│   │   ├── 02-development-process.md
│   │   ├── 03-external-services.md
│   │   ├── 04-planning-pipeline.md
│   │   └── 05-persistence-frontend.md
│   ├── front-docs/
│   │   ├── 前端框架构建方案.md
│   │   ├── 前端界面设计文档.md
│   │   ├── 前端项目完成情况与问题记录.md
│   │   ├── 界面视觉设计系统.md
│   │   └── sse对比测试报告-2026-07-09.md
│   ├── need_fix/
│   │   ├── api-consistency-test-report.md
│   │   ├── backend-checkin-fix.md
│   │   ├── frontend-checkin-fix.md
│   │   ├── 会话管理与方案渲染优化.md
│   │   ├── 前端修改方案.md
│   │   ├── 前端改造方案.md
│   │   ├── 后端修改方案.md
│   │   ├── 导出功能修复方案.md
│   │   ├── 游记模块前端修复方案.md
│   │   ├── 游记模块后端修复方案.md
│   │   └── 远程后端优化方案.md
│   ├── originals/
│   ├── planning/
│   │   ├── agent-date-weather-traffic-task-list.md
│   │   └── 项目优先级清单.md
│   ├── reports/
│   │   ├── 团队创建报告.md
│   │   ├── 项目周报模板.md
│   │   ├── personal/                  # 简历、求职文案与外部项目材料（24 个文件）
│   │   │   └── benchmark/
│   │   ├── CMJ-daily/
│   │   │   └── 第一周项目周报-陈铭杰-2024302111128.md
│   │   ├── FYW-daily/
│   │   │   └── 周报-2026-07-13.md
│   │   ├── TBY-daily/
│   │   │   ├── 2026-07-07-今日提交总结报告.md
│   │   │   ├── 2026-07-08-今日提交总结报告.md
│   │   │   ├── 2026-07-09-今日提交总结报告.md
│   │   │   ├── 2026-07-10-今日提交总结报告.md
│   │   │   ├── 2026-07-11-周报.md
│   │   │   ├── 2026-07-13-今日提交总结报告.md
│   │   │   ├── 2026-07-14-今日提交总结报告.md
│   │   │   ├── 2026-07-15-今日提交总结报告.md
│   │   │   └── 2026-07-16-今日提交总结报告.md
│   │   └── ai-logs/
│   │       ├── README.md
│   │       ├── 2026-07.md
│   │       ├── AI反思日志-Sprint2.md
│   │       ├── Sprint1-AI使用反思报告.md
│   │       ├── Sprint2-AI使用反思报告.md
│   │       └── 陈铭杰-AI使用反思报告-sprint2.md
│   └── requirements/
│       └── 需求设计说明书.md
├── frontend/
│   ├── package.json / package-lock.json
│   ├── vite.config.ts / vitest.config.ts
│   ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
│   └── src/
│       ├── App.vue
│       ├── main.ts
│       ├── env.d.ts
│       ├── api/ (auth, chat, data, http, index, ops, plan, travelogue, trip, user)
│       ├── components/
│       │   ├── auth/ (LoginForm, LoginModal, PhoneVerifyInput, RegisterForm, SmsCodeInput)
│       │   ├── brand/ (AppLogo)
│       │   ├── chat/ (ChatHistory, ChatInput, ChatMessage, FollowUpQuestions, QuickSuggestions, TagInputModal)
│       │   ├── common/ (AppHeader, AppSidebar, ConfirmDialog, EmptyState, ErrorBoundary, LoadingSpinner)
│       │   ├── icons/ (IconTravel)
│       │   ├── layout/ (AppLayout, AuthLayout, PlanLayout, PublicLayout)
│       │   ├── map/ (MapContainer)
│       │   ├── notification/ (InlineAlert, ToastContainer, ToastItem)
│       │   ├── plan/ (ActivityDrawer, ActivityItem, BlockRenderer, BudgetChart, DayCard, ExportDropdown,
│       │   │         PlanCard, PlanHeader, PlanMap, PlanPreview, PlanTimeline, ShareDialog)
│       │   └── trip/ (AdjustmentBanner, CheckInButton, ExpenseSummary, MomentCard, PhotoGrid, ProgressBar, TripTimeline)
│       ├── config/map.ts
│       ├── router/index.ts
│       ├── store/ (authStore, chatStore, planStore, preferenceStore, travelogueStore, tripStore, uiStore)
│       ├── test/
│       │   ├── components/ (ActivityItem, ChatMessage, PlanCard)
│       │   ├── mocks/ (auth, chat, plan)
│       │   ├── stores/ (authStore, chatStore, planStore)
│       │   ├── utils/ (sseParser)
│       │   └── setup.ts
│       ├── types/ (api, auth, chat, common, data, plan, preference)
│       ├── utils/ (planMarkdown, sseParser)
│       └── views/ (ChatPage, ChatSessionPage, HomePage, LoginPage, NotFoundPage, PlanDetailPage,
│                   PlanListPage, PreferencePage, ProfilePage, RegisterPage, TraveloguePage, TripExecutePage)
├── scripts/
│   ├── init_db.py
│   ├── rebuild_vectors.py
│   ├── replace_test_data.py
│   ├── seed_poi.py
│   ├── start_backend.cmd
│   ├── start_backend.ps1
│   ├── start_backend.sh
│   ├── start_frontend.sh
│   ├── test_agent.py
│   ├── test_agents.py
│   ├── test_orchestration.py
│   ├── test_pipeline.py
│   └── test_v2_execution.py
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_api_consistency.py
│   ├── test_conversation_postgres.py
│   ├── test_export_tasks.py
│   ├── test_llm.py
│   ├── test_meituan_config.py
│   ├── test_rag.py
│   └── test_services.py
├── main.py
└── requirements.txt
```

> 本快照只记录纳入版本管理的源文件、脚本和文档，不记录 `__pycache__/`、`builds/`、`cache/`、`chroma_data/` 等本地产物。新增目录、迁移目录、重命名模块或调整入口文件前，必须先说明影响范围并获得用户确认。
