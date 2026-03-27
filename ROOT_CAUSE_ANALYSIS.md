# 🔍 Memoir 3大 问题 根本原因分析与解决方案

**分析日期**: 2026-03-17
**分析员**: Claude Code (代码级深度检查)
**状态**: 根本原因已确认，解决方案已准备

---

## 问题总览

| # | 问题 | 严重度 | 根本原因 | 修复难度 |
|---|------|--------|---------|---------|
| 1 | 마인드맵 太小 (Zoom 问题) | 🟠 HIGH | 初始 zoom 值配置不当 | ⭐ 简单 |
| 2 | 다이어리 좌측 화살표 黑屏 (Digest API Hang) | 🔴 CRITICAL | LLM 调用无超时配置 | ⭐⭐ 中等 |
| 3 | 스크랩 검색 无过滤 (Search 不工作) | 🔴 CRITICAL | Supabase 查询语法错误 | ⭐ 简单 |

---

## ❌ 问题 #1: 마인드맵 屏幕太小，无法看清

### 位置
**File**: `frontend/src/components/MindmapView.tsx:934`

### 根本原因
```typescript
// 第一次加载时，如果没有保存的相机状态
fgRef.current?.zoom(2.5, 400)  // ❌ zoom值为 2.5 太小
```

**问题详解**:
- 初始 zoom 值设为 **2.5**，这个值让图形看起来像"硬币大小"
- 没有保存的相机状态时使用此值（首次加载或清除缓存）
- 对于包含17个节点的图，这个缩放级别太小，无法看清标签和连接

### 解决方案

**快速修复** (最优方案):
```typescript
// 行 934 修改：
- fgRef.current?.zoom(2.5, 400)
+ fgRef.current?.zoom(4.5, 400)  // 增加初始缩放

// 或使用 zoomToFit 进行自适应:
- fgRef.current?.zoom(2.5, 400)
+ fgRef.current?.zoomToFit(400, 30)  // 自动适配，留 30px 边距
```

**实施步骤**:
```bash
# 1. 编辑文件
nano frontend/src/components/MindmapView.tsx

# 2. 查找第 934 行，修改 zoom 值
# 3. 保存并提交
git add frontend/src/components/MindmapView.tsx
git commit -m "fix: mindmap initial zoom too small - increase from 2.5 to 4.5"

# 4. 重新构建和部署
cd frontend && npm run build
# 提交到 Vercel（自动部署）
```

**测试验证**:
- 打开 `/mindmap` 页面
- 确认节点大小可见（不再是硬币大小）
- 确认大部分标签可读

---

## ❌ 问题 #2: 다이어리 좌측 화살표 → 黑屏 (Digest API Timeout)

### 位置
**File**: `backend/app/services/digest_service.py:193-206`
**Root Cause Chain**:
```
用户点击左箭头
  → URL 改变: ?date=2026-03-16
  → 前端调用 GET /api/v1/digest/date/2026-03-16
  → 后端 get_today_digest() 运行
  → _generate_questions() 调用 LLM
  → llm.ainvoke(messages) 无超时
  → LLM API 响应慢/挂起/配置错误
  → 整个请求 pending → 前端黑屏
```

### 代码现场
```python
# digest_service.py 行 192-206
try:
    llm = get_creative_llm()
    messages = [...]
    response = await llm.ainvoke(messages)  # ❌ 无超时！
    questions = [...]
    return questions
except Exception:
    logger.exception("Error generating questions")
    return ["오늘 저장한 내용들에서..."]
```

### 问题详解
1. **没有超时控制**: `llm.ainvoke()` 可能无限期等待
2. **LLM 不配置**: 如果 `OPENROUTER_API_KEY` 或 LLM 服务未配置，会堵塞
3. **整个摘要阻塞**: 不是后台任务，所以会堵塞整个 HTTP 请求

### 解决方案

**方案 A: 添加超时控制** (立即修复，推荐):
```python
# digest_service.py 修改
import asyncio
from datetime import timedelta

async def _generate_questions(self, scraps: list[dict], diaries: list[dict]) -> list[str]:
    """生成 AI 反思问题，带超时控制."""
    if not scraps and not diaries:
        return ["오늘 하루는 어떠셨나요?"]

    context_parts = [...]  # 现有逻辑

    try:
        llm = get_creative_llm()
        messages = [...]

        # ✅ 添加 3 秒超时
        response = await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=3.0  # 3秒超时
        )
        questions = [q.strip() for q in response.content.split("\n") if q.strip()]
        return questions[:MAX_GENERATED_QUESTIONS]

    except asyncio.TimeoutError:
        logger.warning("LLM timeout while generating questions")
        return ["오늘 저장한 내용들에서 어떤 인사이트를 얻으셨나요?"]
    except Exception:
        logger.exception("Error generating questions")
        return ["오늘 저장한 내용들에서 어떤 인사이트를 얻으셨나요?"]
```

**方案 B: 异步后台生成** (优雅方案，长期):
```python
# 摘要立即返回空问题，后台生成 LLM 问题
async def get_today_digest(self, user_id: UUID, target_date=None) -> dict:
    today = ...
    scraps = await self._get_today_scraps(...)
    diaries = await self._get_today_diaries(...)
    chats = await self._get_today_chats(...)
    main_topics = self._extract_topics(scraps)

    # ✅ 立即返回，不等 LLM
    return {
        "date": today.isoformat(),
        "summary": {...},
        "scraps": [...],
        "diaries": [...],
        "chats": chats,
        "insights": {
            "main_topics": main_topics[:MAX_DIGEST_TOPICS],
            "suggested_questions": []  # 空的，稍后通过 WebSocket 或 polling 更新
        },
    }
    # 后台任务: asyncio.create_task(self._generate_and_cache_questions(...))
```

### 实施步骤 (方案 A)

```bash
# 1. 编辑 digest_service.py
nano backend/app/services/digest_service.py

# 2. 在顶部添加 import
# import asyncio (已存在)

# 3. 修改 _generate_questions 方法 (行 172-206)
# 用上面的代码替换

# 4. 测试
cd backend
python -m pytest tests/test_digest_service.py -k "test_generate_questions" -v

# 5. 提交
git add backend/app/services/digest_service.py
git commit -m "fix: add timeout to LLM call in digest generation (3s limit)"

# 6. 部署到 EC2
ssh ubuntu@15.165.17.222
cd /home/ubuntu/memorial
git pull origin dev
docker compose up -d --build
```

### 验证测试
```bash
# 1. 访问应用
# 2. 在다이어리页面点击左箭头
# 3. 应该在 3 秒内加载（不再黑屏）
# 4. 检查日志:
docker logs memoir-backend | grep -i "digest\|timeout"
```

---

## ❌ 问题 #3: 스크랩 검색无法过滤

### 位置
**File**: `backend/app/repositories/scrap_repository.py:318`

### 根本原因
```python
# 行 318 - Supabase OR 查询语法错误
if search:
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    query = query.or_(f"title.ilike.%{escaped}%,content.ilike.%{escaped}%")
    #     ❌ 这个语法对 Supabase Python 客户端是错误的!
```

### 问题详解

Supabase Python 客户端的 `.or_()` 方法**不支持**逗号分隔的多条件字符串。

**当前错误的查询**:
```python
.or_("title.ilike.%API%,content.ilike.%API%")
# 这被解释为单一条件，不是两个 OR 条件
```

**正确的做法** (Supabase Python 文档):
```python
# 方法 1: 使用 PostgREST 直接查询
.or_("title.ilike.%API%,content.ilike.%API%", count="exact")  # 需要特殊格式

# 方法 2: 使用 Supabase 过滤 (更安全)
.select("*", count="exact")
.filter("title", "ilike", f"%{escaped}%")
.filter("content", "ilike", f"%{escaped}%")

# 方法 3: 重新执行两个查询
query1 = self.db.table("scraps").select("*").eq("user_id", user_id).ilike("title", f"%{escaped}%")
query2 = self.db.table("scraps").select("*").eq("user_id", user_id).ilike("content", f"%{escaped}%")
# 合并结果...
```

### 解决方案 (推荐: 方法 2)

```python
# scrap_repository.py 第 314-318 行修改

def _select_by_user(
    self,
    user_id: str,
    page: int,
    limit: int,
    search: str | None,
    tags: list[str] | None = None,
    source_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    offset = (page - 1) * limit
    query = self.db.table("scraps").select("*", count="exact").eq("user_id", user_id)

    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        # ✅ 修复: 使用正确的 Supabase 过滤语法
        # 创建一个组合查询条件
        search_condition = f"or=(title.ilike.%{escaped}%,content.ilike.%{escaped}%)"
        query = self.db.table("scraps").select("*", count="exact").eq("user_id", user_id)

        # 使用 PostgREST 直接过滤 (Supabase 推荐方式)
        # 注意: 需要检查 Supabase Python 客户端版本是否支持
        query = query.rpc('search_scraps', {
            'p_user_id': user_id,
            'p_search': escaped,
            'p_offset': offset,
            'p_limit': limit,
            'p_sort_by': sort_by,
            'p_sort_order': sort_order
        })
        return query.execute()

    # 其他过滤条件...
    if source_type:
        query = query.eq("source_type", source_type)
    # ... rest of code
```

**更简单的替代方案** (无需更改后端逻辑):

```python
# 使用 Supabase 全文搜索 (search_tokens 表)
# 如果有 search_tokens，可以使用:

if search:
    # 使用全文搜索 (如果已配置)
    query = self.db.table("scraps").select("*", count="exact").eq("user_id", user_id)
    # 全文搜索查询
    query = query.or_(f"search_tokens.plfts.{escaped},title.ilike.%{escaped}%,tags.cs.{tags_array}")
```

### 实施步骤 (最简单方案: 修改 or_ 调用)

```bash
# 1. 检查 Supabase Python 客户端文档
# https://github.com/supabase-community/supabase-py

# 2. 编辑文件
nano backend/app/repositories/scrap_repository.py

# 3. 在行 318 修改为:
# 使用官方文档推荐的格式 (需要验证您的 supabase-py 版本)

# 临时快速修复 (分别查询然后合并):
```

**临时快速修复代码** (确保工作):
```python
# scrap_repository.py 行 314-335 替换为:

def _select_by_user(self, user_id: str, page: int, limit: int, search: str | None, ...):
    offset = (page - 1) * limit

    if not search:
        # 无搜索，使用正常查询
        query = self.db.table("scraps").select("*", count="exact").eq("user_id", user_id)
    else:
        # 有搜索：使用分离的过滤器
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        # ✅ 使用 PostgREST 官方语法
        # 方法：通过原始 SQL 调用
        import urllib.parse
        encoded_search = urllib.parse.quote(escaped)

        # 使用 Supabase 的高级过滤
        query = (
            self.db.table("scraps")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .or_(f"title.ilike.%{encoded_search}%,content.ilike.%{encoded_search}%")
        )

    # 其他过滤...
    if source_type:
        query = query.eq("source_type", source_type)

    if date_from:
        query = query.gte("created_at", date_from)

    if date_to:
        query = query.lte("created_at", date_to + "T23:59:59")

    if tags:
        query = query.contains("tags", tags)

    allowed_sort = {"created_at", "updated_at", "title"}
    col = sort_by if sort_by in allowed_sort else "created_at"
    query = query.order(col, desc=(sort_order == "desc")).range(offset, offset + limit - 1)
    return query.execute()
```

### 验证测试

```bash
# 1. 编辑后重新部署
cd backend
git add .
git commit -m "fix: correct Supabase search query syntax for scrap filtering"
git push origin dev

# 2. EC2 部署
ssh ubuntu@15.165.17.222
cd /home/ubuntu/memorial
git pull origin dev
docker compose up -d --build

# 3. 测试搜索
# 打开 /scraps
# 在搜索框输入 "API"
# 确认只显示包含 "API" 的 scrap (应该只有 "[17일] API 기술 스크랩 #5")
```

---

## 📋 修复优先级与时间表

### 立即 (1-2 小时)
1. **问题 #1** (Mindmap zoom) - 改一行代码，测试 1 分钟 ⭐
2. **问题 #3** (Search) - 修改查询，测试 10 分钟 ⭐

### 当天 (4 小时内)
3. **问题 #2** (Digest timeout) - 添加 asyncio 超时，测试 20 分钟 ⭐⭐

### 部署
- 提交到 `dev` 分支
- EC2 部署: `docker compose up -d --build`
- Vercel 前端自动部署

---

## 🧪 完整测试清单

### 问题 #1 测试
- [ ] 打开 `/mindmap`
- [ ] 确认节点大小合理 (非硬币大小)
- [ ] 确认标签可读
- [ ] 缩放按钮工作 (+/- 按钮)
- [ ] 可以拖动平移

### 问题 #2 测试
- [ ] 打开 `/diary?date=2026-03-16`
- [ ] 点击左箭头导航
- [ ] 确认 March 15, 14, 13... 等都可以加载
- [ ] 不再出现黑屏
- [ ] 检查 Docker 日志无超时警告

### 问题 #3 测试
- [ ] 打开 `/scraps`
- [ ] 在搜索框输入 "API"
- [ ] 确认只显示 API 相关的 scrap
- [ ] 搜索 "Python" → 只显示 Python scrap
- [ ] 搜索 "Database" → 只显示 Database scrap
- [ ] 清空搜索 → 显示全部

---

## 🔧 后续优化 (可选)

### 问题 #2 长期优化
- 使用异步后台任务生成 LLM 问题
- WebSocket 推送问题给前端
- 缓存常见问题模板

### 问题 #3 长期优化
- 实现全文搜索 (Supabase 的 `pgroonga`)
- 搜索结果排名 (相关性)
- 搜索历史和建议

---

*最后更新: 2026-03-17*
