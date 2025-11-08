# Gemini CLI 429 错误说明

## 问题现象

```
✖ Error generating JSON content via API
⚠ Attempt 1 failed with status 429. Retrying with backoff...
   "code": 429,
   "message": "Resource exhausted. Please try again later."
   "reason": "rateLimitExceeded"
```

---

## 🔍 这是什么错误？

**429 错误是 Google Gemini API 的配额限制（Rate Limiting）**

- **不是** TigerHill 的问题
- **不是** interceptor 导致的
- **是** Google Cloud 的 API 使用限制

---

## 📊 限流规则

### 免费账户

- **每分钟请求数 (RPM)**: ~15 requests
- **每天请求数 (RPD)**: ~1,500 requests
- **令牌数限制**: varies by model

### 付费账户

- 更高的配额
- 可以申请增加配额

---

## ✅ 解决方法

### 方法 1: 等待（最简单）

```bash
# 等待 1-5 分钟后再试
sleep 300  # 5 分钟

# 然后重新运行
./scripts/test_gemini_fixed.sh
```

### 方法 2: 检查配额使用情况

访问 Google Cloud Console:
```
https://console.cloud.google.com/iam-admin/quotas
```

查看：
- Gemini API 的配额使用情况
- 是否接近限制
- 当前配额限制值

### 方法 3: 申请提高配额

1. 访问 Google Cloud Console
2. 导航到 "IAM & Admin" > "Quotas"
3. 搜索 "Gemini" 或 "Generative Language"
4. 选择要增加的配额
5. 点击 "Edit Quotas"
6. 提交增加请求

### 方法 4: 升级到付费账户

免费账户有严格限制，付费账户配额更高：
- https://cloud.google.com/vertex-ai/pricing

### 方法 5: 使用不同的 Google 账户

```bash
# 重新认证到不同账户
gcloud auth login

# 或使用不同的 API key
export GOOGLE_API_KEY="your-different-api-key"
```

### 方法 6: 添加重试逻辑（已内置）

Gemini CLI 已经自动重试：
```
⚠ Attempt 1 failed with status 429. Retrying with backoff...
```

耐心等待即可，通常会在几次重试后成功。

---

## 🔧 与 TigerHill 一起使用

### TigerHill 不会增加 API 调用次数

- ✅ TigerHill 只是**旁观者**，复制数据副本
- ✅ 不发送额外的 API 请求
- ✅ 不影响配额使用

### 验证 TigerHill 是否工作

即使遇到 429 错误，TigerHill 也应该能捕获到请求和错误响应：

```bash
# 查看捕获文件
ls -lh ./prompt_captures/gemini_cli/

# 查看内容
cat ./prompt_captures/gemini_cli/session_*.json | python -m json.tool
```

应该能看到：
```json
{
  "turns": [
    {
      "requests": [...],  // 你的请求
      "responses": [
        {
          "status_code": 429,  // 错误响应
          "raw_text": "Resource exhausted..."
        }
      ]
    }
  ]
}
```

---

## 🎯 测试建议

### 1. 先测试不带 TigerHill

```bash
# 不使用 interceptor
node ../gemini-cli/bundle/gemini.js
```

如果这也出现 429 错误，说明：
- ✅ 确认是 API 配额问题
- ✅ 不是 TigerHill 的问题

### 2. 使用简单的 prompt

避免复杂的、需要多次 API 调用的任务：

```bash
# ✅ 简单任务
> 1+1等于几？

# ❌ 复杂任务（会触发多次 API 调用）
> 帮我创建一个完整的 Web 应用，包括前端、后端、数据库...
```

### 3. 分散测试时间

不要在短时间内频繁测试：

```bash
# ❌ 错误做法
for i in {1..10}; do
    ./test.sh  # 快速循环测试
done

# ✅ 正确做法
./test.sh
sleep 60  # 等待 1 分钟
./test.sh
```

---

## 📝 错误日志位置

Gemini CLI 会保存详细错误报告：

```
/var/folders/ym/.../gemini-client-error-generateJson-api-2025-11-07T11-43-43-488Z.json
```

查看内容：
```bash
cat /var/folders/*/gemini-client-error-*.json | python -m json.tool
```

---

## 🔍 诊断步骤

使用 TigerHill 诊断脚本：

```bash
cd /Users/yinaruto/MyProjects/ChatLLM/TigerHill
./scripts/diagnose_gemini.sh
```

这将：
1. 测试不带 interceptor 的 Gemini CLI
2. 测试带 interceptor 的 Gemini CLI
3. 对比两者的行为
4. 检查是否捕获到数据
5. 分析错误原因

---

## 💡 常见问题

### Q: 为什么我的第一次请求就 429？

A: 可能是：
1. 之前已经用完了配额
2. 配额在整个 Google 账户级别共享
3. 其他项目也在使用同一个 API

### Q: TigerHill 会让 429 错误更频繁吗？

A: **不会**。TigerHill 不发送额外请求，只是复制数据。

### Q: 遇到 429 时 TigerHill 能捕获吗？

A: **能**。TigerHill 会捕获 429 响应，包括：
- 状态码 429
- 错误消息
- Headers
- 完整的错误 JSON

### Q: 如何避免 429 错误？

A:
1. 减少请求频率
2. 使用付费账户
3. 申请提高配额
4. 使用多个 API key 轮换

---

## 🎓 学到的东西

### 1. 429 不是 bug，是保护机制

Google 用 429 保护服务器不被滥用。

### 2. TigerHill 是透明的

不会增加 API 调用，不会导致 429。

### 3. 捕获错误也很有价值

即使是错误响应，TigerHill 也会记录，帮助你：
- 分析失败原因
- 统计错误率
- 改进 prompt

---

## 📚 相关文档

- [Google Cloud 429 错误文档](https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429)
- [Gemini API 配额](https://ai.google.dev/gemini-api/docs/quota)
- [Google Cloud 配额管理](https://console.cloud.google.com/iam-admin/quotas)

---

## 总结

**429 错误 = API 配额限制**

- ❌ 不是 TigerHill 的问题
- ❌ 不是 interceptor 的 bug
- ✅ 是 Google API 的正常限流机制

**解决方法**:
1. 等待几分钟
2. 检查配额
3. 升级账户
4. 使用不同账户

**TigerHill 的行为**:
- ✅ 完全透明，不影响配额
- ✅ 能捕获 429 错误响应
- ✅ 帮助你分析 API 使用情况
