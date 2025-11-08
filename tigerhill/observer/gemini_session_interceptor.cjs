/**
 * TigerHill Session-Aware Interceptor for Gemini CLI (Fixed Version)
 *
 * 修复了响应流消费问题：
 * - 使用透明代理模式，不消费原始响应流
 * - 让数据同时流向 TigerHill 和 Gemini CLI
 * - 保证 Gemini CLI 能正常接收响应
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const zlib = require('zlib');
const { PassThrough } = require('stream');

// 配置
const EXPORT_DIR = process.env.TIGERHILL_CAPTURE_PATH || path.resolve(process.cwd(), 'prompt_captures');
const GEMINI_API_HOSTS = [
    'generativelanguage.googleapis.com',
    'cloudcode-pa.googleapis.com',
    'aiplatform.googleapis.com',
    'content-aiplatform.googleapis.com'
];

// 确保导出目录存在
if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
}

// 会话存储
const SESSION_STORE = path.join(EXPORT_DIR, '.session_store.json');
const PROCESS_ID = `pid_${process.pid}_${Date.now()}`;

let sessions = {};
if (fs.existsSync(SESSION_STORE)) {
    try {
        sessions = JSON.parse(fs.readFileSync(SESSION_STORE, 'utf8'));
    } catch (e) {
        console.error('[TigerHill] Failed to load session store:', e.message);
        sessions = {};
    }
}

console.log('[TigerHill Session Interceptor - Fixed] Active');
console.log(`[TigerHill] Process ID: ${PROCESS_ID}`);
console.log(`[TigerHill] Export directory: ${EXPORT_DIR}`);

// 保存会话存储
function saveSessionStore() {
    try {
        fs.writeFileSync(SESSION_STORE, JSON.stringify(sessions, null, 2));
    } catch (e) {
        console.error('[TigerHill] Failed to save session store:', e);
    }
}

// 获取或创建会话
function getOrCreateSession(sessionId) {
    if (!sessionId) {
        sessionId = `conv_${crypto.randomUUID()}`;
    }

    if (!sessions[sessionId]) {
        sessions[sessionId] = {
            session_id: sessionId,
            conversation_id: sessionId,
            agent_name: 'gemini-cli',
            start_time: Date.now() / 1000,
            capture_file: path.join(EXPORT_DIR, `session_${sessionId}_${Date.now()}.json`),
            turns: [],
            conversation_history: {
                system_prompt: null,
                messages: [],
                total_turns: 0
            },
            metadata: {
                tool: 'gemini-cli',
                interceptor: 'session-aware-fixed',
                version: '2.1',
                phase: 'bugfix-stream-consumption',
                processes: []
            }
        };
    }

    if (!sessions[sessionId].metadata.processes.includes(PROCESS_ID)) {
        sessions[sessionId].metadata.processes.push(PROCESS_ID);
    }

    return sessions[sessionId];
}

// 保存会话数据
function saveSession(session) {
    try {
        const data = {
            ...session,
            end_time: Date.now() / 1000,
            duration: (Date.now() / 1000) - session.start_time,
            statistics: {
                total_turns: session.turns.length,
                total_requests: session.turns.reduce((sum, t) => sum + t.requests.length, 0),
                total_responses: session.turns.reduce((sum, t) => sum + t.responses.length, 0),
                total_tokens: session.turns.reduce((sum, t) => {
                    return sum + t.responses.reduce((s, r) => s + (r.usage?.total_tokens || 0), 0);
                }, 0),
                conversation_statistics: {
                    total_messages: session.conversation_history.messages.length,
                    system_messages: session.conversation_history.messages.filter(m => m.role === 'system').length,
                    user_messages: session.conversation_history.messages.filter(m => m.role === 'user').length,
                    assistant_messages: session.conversation_history.messages.filter(m => m.role === 'assistant').length,
                    has_system_prompt: !!session.conversation_history.system_prompt,
                    conversation_turns: session.conversation_history.total_turns
                }
            }
        };

        fs.writeFileSync(session.capture_file, JSON.stringify(data, null, 2));
        saveSessionStore();
    } catch (error) {
        console.error('[TigerHill] Failed to save session:', error);
    }
}

// 当前轮次追踪
const currentTurn = {
    requests: [],
    responses: []
};
let currentSessionId = null;

// 保存原始 https.request
const originalHttpsRequest = https.request;

// Hook https.request
https.request = function(options, callback) {
    // 检查是否是 Gemini API 请求
    const isGeminiRequest =
        (typeof options === 'string' && GEMINI_API_HOSTS.some(host => options.includes(host))) ||
        (typeof options === 'object' && (
            GEMINI_API_HOSTS.includes(options.hostname) ||
            GEMINI_API_HOSTS.includes(options.host) ||
            (options.href && GEMINI_API_HOSTS.some(host => options.href.includes(host)))
        ));

    if (!isGeminiRequest) {
        return originalHttpsRequest.apply(this, arguments);
    }

    if (process.env.TIGERHILL_DEBUG === 'true') {
        console.log('[TigerHill] Intercepting Gemini API request');
    }

    // 捕获请求数据
    let requestBody = '';
    const requestId = crypto.randomUUID();
    const requestTime = Date.now();

    const requestData = {
        request_id: requestId,
        timestamp: requestTime / 1000,
        method: options.method || 'POST',
        url: typeof options === 'string' ? options : `https://${options.hostname || options.host}${options.path || ''}`,
        headers: options.headers || {}
    };

    // ✅ 修复：创建包装的 callback，而不是替换响应处理
    const wrappedCallback = callback ? function(res) {
        // 为 TigerHill 捕获创建一个数据副本流
        const chunks = [];

        // ✅ 关键修复：不直接监听原始 res 的事件
        // 而是先让原始 callback 处理，同时复制数据

        // 保存原始的 emit 方法
        const originalEmit = res.emit.bind(res);

        // 包装 emit 方法来捕获数据
        res.emit = function(event, ...args) {
            // 如果是 data 事件，复制数据
            if (event === 'data' && args[0]) {
                chunks.push(Buffer.from(args[0]));
            }

            // 如果是 end 事件，处理捕获的数据
            if (event === 'end') {
                // 异步处理，不阻塞原始流程
                setImmediate(() => {
                    processCapturedResponse(chunks, res, requestId, requestTime, requestData);
                });
            }

            // 调用原始 emit，让数据正常流向 Gemini CLI
            return originalEmit(event, ...args);
        };

        // 调用原始 callback，让 Gemini CLI 正常处理响应
        callback(res);
    } : undefined;

    // 创建代理请求对象
    const req = originalHttpsRequest(options, wrappedCallback);

    // Hook write 方法
    const originalWrite = req.write.bind(req);
    req.write = function(chunk, encoding, callback) {
        if (chunk) {
            requestBody += chunk.toString();
        }
        return originalWrite(chunk, encoding, callback);
    };

    // Hook end 方法
    const originalEnd = req.end.bind(req);
    req.end = function(chunk, encoding, callback) {
        if (chunk) {
            requestBody += chunk.toString();
        }

        try {
            // 解析请求
            try {
                const parsedRequest = JSON.parse(requestBody);

                // 提取会话 ID
                if (parsedRequest.request?.session_id) {
                    currentSessionId = parsedRequest.request.session_id;
                    if (process.env.TIGERHILL_DEBUG === 'true') {
                        console.log(`[TigerHill] Session ID: ${currentSessionId}`);
                    }
                }

                // 提取模型信息
                if (parsedRequest.model) {
                    requestData.model = parsedRequest.model;
                }

                // 提取 prompt 和系统指令
                if (parsedRequest.request?.contents) {
                    requestData.contents = parsedRequest.request.contents;

                    const userContents = parsedRequest.request.contents.filter(c => c.role === 'user');
                    if (userContents.length > 0) {
                        const lastUserContent = userContents[userContents.length - 1];
                        if (lastUserContent.parts) {
                            const textParts = lastUserContent.parts
                                .filter(p => p.text)
                                .map(p => p.text);
                            requestData.user_input = textParts.join('\n');
                        }
                    }

                    requestData.conversation_length = parsedRequest.request.contents.length;
                }

                if (parsedRequest.request?.systemInstruction) {
                    requestData.system_instruction = parsedRequest.request.systemInstruction;

                    if (parsedRequest.request.systemInstruction.parts) {
                        const systemTexts = parsedRequest.request.systemInstruction.parts
                            .filter(p => p.text)
                            .map(p => p.text);
                        requestData.system_prompt = systemTexts.join('\n');
                    }
                }

                if (parsedRequest.request?.generationConfig) {
                    requestData.generation_config = parsedRequest.request.generationConfig;
                }

                if (process.env.TIGERHILL_SAVE_RAW === 'true') {
                    requestData.raw_request = parsedRequest;
                }
            } catch (e) {
                requestData.raw_body = requestBody;
            }

            currentTurn.requests.push(requestData);

        } catch (error) {
            console.error('[TigerHill] Failed to capture request:', error);
        }

        return originalEnd(chunk, encoding, callback);
    };

    return req;
};

// ✅ 新增：异步处理捕获的响应数据
function processCapturedResponse(chunks, res, requestId, requestTime, requestData) {
    try {
        const responseData = {
            request_id: requestId,
            timestamp: Date.now() / 1000,
            duration_ms: Date.now() - requestTime,
            status_code: res.statusCode,
            headers: Object.fromEntries(Object.entries(res.headers))
        };

        // 合并所有chunks
        let responseBuffer = Buffer.concat(chunks);

        // 检查是否是gzip压缩
        const encoding = res.headers['content-encoding'];
        try {
            if (encoding === 'gzip') {
                responseBuffer = zlib.gunzipSync(responseBuffer);
                if (process.env.TIGERHILL_DEBUG === 'true') {
                    console.log('[TigerHill Debug] Successfully decompressed gzip response');
                }
            } else if (encoding === 'deflate') {
                responseBuffer = zlib.inflateSync(responseBuffer);
                if (process.env.TIGERHILL_DEBUG === 'true') {
                    console.log('[TigerHill Debug] Successfully decompressed deflate response');
                }
            }
        } catch (decompressError) {
            console.error(`[TigerHill] Failed to decompress response: ${decompressError.message}`);
            responseData.decompress_error = decompressError.message;
            currentTurn.responses.push(responseData);
            return;
        }

        const responseBody = responseBuffer.toString('utf-8');

        if (process.env.TIGERHILL_DEBUG === 'true') {
            console.log(`[TigerHill Debug] Response body length: ${responseBody.length}`);
            console.log(`[TigerHill Debug] Response preview: ${responseBody.substring(0, 200)}`);
        }

        // 解析响应 - 支持SSE流式格式和普通JSON
        try {
            // 检查是否是SSE格式
            if (responseBody.startsWith('data: ')) {
                const lines = responseBody.split('\n');
                const textParts = [];
                let lastUsageMetadata = null;
                let lastFinishReason = null;

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.substring(6);
                            const chunk = JSON.parse(jsonStr);

                            const response = chunk.response || chunk;
                            if (response.candidates && response.candidates[0]) {
                                const candidate = response.candidates[0];

                                if (candidate.content?.parts) {
                                    const parts = candidate.content.parts
                                        .filter(p => p.text && !p.thought)
                                        .map(p => p.text);
                                    textParts.push(...parts);
                                }

                                if (candidate.finishReason) {
                                    lastFinishReason = candidate.finishReason;
                                }
                            }

                            if (response.usageMetadata) {
                                lastUsageMetadata = response.usageMetadata;
                            }
                        } catch (lineError) {
                            // 跳过无法解析的行
                        }
                    }
                }

                responseData.text = textParts.join('');
                responseData.finish_reason = lastFinishReason;

                if (lastUsageMetadata) {
                    responseData.usage = {
                        prompt_tokens: lastUsageMetadata.promptTokenCount || 0,
                        completion_tokens: lastUsageMetadata.candidatesTokenCount || 0,
                        total_tokens: lastUsageMetadata.totalTokenCount || 0
                    };
                }

                if (process.env.TIGERHILL_DEBUG === 'true') {
                    console.log(`[TigerHill Debug] Parsed SSE response: ${textParts.length} text parts, ${responseData.text.length} chars`);
                }
            } else {
                // 普通JSON响应
                const parsedResponse = JSON.parse(responseBody);

                if (parsedResponse.candidates) {
                    const candidate = parsedResponse.candidates[0];
                    if (candidate?.content?.parts) {
                        const textParts = candidate.content.parts
                            .filter(p => p.text)
                            .map(p => p.text);
                        responseData.text = textParts.join('\n');
                    }
                    responseData.finish_reason = candidate?.finishReason;
                }

                if (parsedResponse.usageMetadata) {
                    responseData.usage = {
                        prompt_tokens: parsedResponse.usageMetadata.promptTokenCount,
                        completion_tokens: parsedResponse.usageMetadata.candidatesTokenCount,
                        total_tokens: parsedResponse.usageMetadata.totalTokenCount
                    };
                }

                if (process.env.TIGERHILL_SAVE_RAW === 'true') {
                    responseData.raw_response = parsedResponse;
                }
            }
        } catch (e) {
            console.error(`[TigerHill] Failed to parse response: ${e.message}`);
            responseData.raw_text = responseBody.substring(0, 10000);
            responseData.parse_error = e.message;
        }

        currentTurn.responses.push(responseData);

        // 如果这是一个完整的对话轮次，保存
        if (currentSessionId && requestData.url.includes('generateContent')) {
            const session = getOrCreateSession(currentSessionId);
            const turnNumber = session.turns.length + 1;

            session.turns.push({
                turn_number: turnNumber,
                timestamp: requestTime / 1000,
                requests: [...currentTurn.requests],
                responses: [...currentTurn.responses]
            });

            updateConversationHistory(session, turnNumber, responseData);

            saveSession(session);

            if (process.env.TIGERHILL_DEBUG === 'true') {
                console.log(`[TigerHill] Saved turn #${turnNumber} for session ${currentSessionId}`);
            }

            // 重置当前轮次
            currentTurn.requests = [];
            currentTurn.responses = [];
        }

    } catch (error) {
        console.error('[TigerHill] Failed to process captured response:', error);
    }
}

// 结构化对话历史支持函数
function addUserMessageToHistory(session, turnNumber, requestData) {
    const history = session.conversation_history;

    if (turnNumber === 1 && requestData.system_prompt && !history.system_prompt) {
        history.system_prompt = requestData.system_prompt;

        history.messages.push({
            role: 'system',
            content: requestData.system_prompt,
            turn_number: 0,
            message_index: history.messages.length,
            timestamp: requestData.timestamp
        });
    }

    const userMessage = {
        role: 'user',
        content: requestData.user_input || '',
        turn_number: turnNumber,
        message_index: history.messages.length,
        timestamp: requestData.timestamp,
        metadata: {
            request_id: requestData.request_id,
            model: requestData.model,
            conversation_length: requestData.conversation_length
        }
    };

    history.messages.push(userMessage);
    history.total_turns = Math.max(history.total_turns, turnNumber);
}

function addAssistantMessageToHistory(session, turnNumber, responseData) {
    const history = session.conversation_history;

    const assistantMessage = {
        role: 'assistant',
        content: responseData.text || '',
        turn_number: turnNumber,
        message_index: history.messages.length,
        timestamp: responseData.timestamp,
        metadata: {
            request_id: responseData.request_id,
            finish_reason: responseData.finish_reason,
            duration_ms: responseData.duration_ms
        },
        tokens_used: responseData.usage || null
    };

    history.messages.push(assistantMessage);
}

function updateConversationHistory(session, turnNumber, responseData) {
    const currentRequests = currentTurn.requests;
    if (currentRequests.length > 0) {
        const requestData = currentRequests[0];
        addUserMessageToHistory(session, turnNumber, requestData);
    }

    addAssistantMessageToHistory(session, turnNumber, responseData);
}

// 进程退出时保存所有会话
process.on('exit', () => {
    if (currentSessionId && (currentTurn.requests.length > 0 || currentTurn.responses.length > 0)) {
        const session = getOrCreateSession(currentSessionId);
        session.turns.push({
            turn_number: session.turns.length + 1,
            timestamp: Date.now() / 1000,
            requests: currentTurn.requests,
            responses: currentTurn.responses
        });
        saveSession(session);
    }
    console.log(`[TigerHill] Process ${PROCESS_ID} exiting`);
});

process.on('SIGINT', () => {
    console.log('\n[TigerHill] Interrupted, saving sessions...');
    process.exit(0);
});

console.log('[TigerHill Session Interceptor - Fixed] Ready to capture multi-turn conversations');
