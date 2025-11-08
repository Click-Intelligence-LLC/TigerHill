/**
 * TigerHill Fetch Interceptor for Gemini CLI
 *
 * 通过拦截原生 fetch API 来捕获 Gemini API 的完整交互
 * 适用于使用 @google/genai SDK 的应用（如 gemini-cli）
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// 配置
const EXPORT_DIR = process.env.TIGERHILL_CAPTURE_PATH || path.resolve(process.cwd(), 'prompt_captures');
const GEMINI_API_HOSTS = [
    'generativelanguage.googleapis.com',
    'aiplatform.googleapis.com',
    'content-aiplatform.googleapis.com'
];

// 确保导出目录存在
if (!fs.existsSync(EXPORT_DIR)) {
    fs.mkdirSync(EXPORT_DIR, { recursive: true });
}

// 生成捕获ID
const CAPTURE_ID = crypto.randomUUID();
const CAPTURE_FILE = path.join(EXPORT_DIR, `capture_${CAPTURE_ID}_${Date.now()}.json`);

// 捕获数据结构
const captureData = {
    capture_id: CAPTURE_ID,
    agent_name: 'gemini_cli',
    start_time: Date.now() / 1000,
    metadata: {
        tool: 'gemini-cli',
        interceptor: 'fetch',
        version: '1.0'
    },
    requests: [],
    responses: []
};

console.log('[TigerHill Fetch Interceptor] Active');
console.log(`[TigerHill Fetch Interceptor] Capture file: ${CAPTURE_FILE}`);

// 保存原始 fetch
const originalFetch = globalThis.fetch;

// Hook fetch
globalThis.fetch = async function(resource, options = {}) {
    // 提取 URL
    let url;
    if (typeof resource === 'string') {
        url = resource;
    } else if (resource && typeof resource === 'object' && resource.url) {
        url = resource.url;
    } else {
        // 不是我们能处理的请求，直接透传
        return originalFetch.apply(this, arguments);
    }

    // 检查是否是 Gemini API 请求
    const isGeminiRequest = GEMINI_API_HOSTS.some(host => url.includes(host));

    if (!isGeminiRequest) {
        // 非 Gemini 请求，直接透传
        return originalFetch.apply(this, arguments);
    }

    console.log('[TigerHill] Intercepting Gemini API fetch request');
    console.log(`[TigerHill] URL: ${url}`);

    // 捕获请求数据
    const requestId = crypto.randomUUID();
    const requestTime = Date.now();

    const requestData = {
        request_id: requestId,
        timestamp: requestTime / 1000,
        method: options.method || 'GET',
        url: url,
        headers: options.headers || {}
    };

    // 捕获请求体
    let requestBody = null;
    if (options.body) {
        if (typeof options.body === 'string') {
            requestBody = options.body;
        } else if (options.body instanceof Buffer) {
            requestBody = options.body.toString();
        } else {
            try {
                requestBody = JSON.stringify(options.body);
            } catch (e) {
                requestBody = String(options.body);
            }
        }

        // 解析并提取关键信息
        try {
            const parsedRequest = JSON.parse(requestBody);

            // 提取模型信息
            const modelMatch = url.match(/models\/([\w\-\.]+)/);
            if (modelMatch) {
                requestData.model = modelMatch[1];
            }

            // 提取 prompt/contents
            if (parsedRequest.contents) {
                requestData.contents = parsedRequest.contents;

                // 提取纯文本
                const textParts = extractTextFromContents(parsedRequest.contents);
                if (textParts.length > 0) {
                    requestData.prompt_text = textParts.join('\n\n---\n\n');
                }
            }

            // 提取系统指令
            if (parsedRequest.systemInstruction) {
                requestData.system_instruction = parsedRequest.systemInstruction;

                const systemTexts = extractTextFromParts(parsedRequest.systemInstruction.parts);
                if (systemTexts.length > 0) {
                    requestData.system_prompt = systemTexts.join('\n');
                }
            }

            // 提取生成配置
            if (parsedRequest.generationConfig) {
                requestData.generation_config = parsedRequest.generationConfig;
            }

            // 提取工具配置
            if (parsedRequest.tools) {
                requestData.tools = parsedRequest.tools.map(tool => {
                    if (tool.functionDeclarations) {
                        return {
                            type: 'function_declarations',
                            functions: tool.functionDeclarations.map(f => ({
                                name: f.name,
                                description: f.description
                            }))
                        };
                    }
                    if (tool.codeExecution) {
                        return { type: 'code_execution' };
                    }
                    return tool;
                });
            }

            // 提取安全设置
            if (parsedRequest.safetySettings) {
                requestData.safety_settings = parsedRequest.safetySettings;
            }

            // 保存完整请求（可选，如果需要调试）
            if (process.env.TIGERHILL_SAVE_RAW === 'true') {
                requestData.raw_request = parsedRequest;
            }
        } catch (e) {
            // 解析失败，保存原始body
            console.warn('[TigerHill] Failed to parse request body:', e.message);
            requestData.raw_body = requestBody;
        }
    }

    captureData.requests.push(requestData);
    saveCapture();

    // 执行原始请求
    const startTime = Date.now();
    let response;
    let error = null;

    try {
        response = await originalFetch.apply(this, arguments);

        // 克隆响应以便我们可以读取它
        const responseClone = response.clone();

        // 捕获响应
        const responseData = {
            request_id: requestId,
            timestamp: Date.now() / 1000,
            duration_ms: Date.now() - startTime,
            status_code: response.status,
            status_text: response.statusText,
            headers: Object.fromEntries(response.headers.entries())
        };

        // 读取响应体
        try {
            const responseText = await responseClone.text();

            // 尝试解析 JSON
            try {
                const parsedResponse = JSON.parse(responseText);

                // 提取 Gemini 响应内容
                if (parsedResponse.candidates) {
                    const candidate = parsedResponse.candidates[0];

                    if (candidate && candidate.content) {
                        // 提取文本
                        const textParts = extractTextFromParts(candidate.content.parts);
                        if (textParts.length > 0) {
                            responseData.text = textParts.join('\n');
                        }

                        // 提取工具调用
                        const toolCalls = extractToolCalls(candidate.content.parts);
                        if (toolCalls.length > 0) {
                            responseData.tool_calls = toolCalls;
                        }
                    }

                    responseData.finish_reason = candidate?.finishReason;
                    responseData.safety_ratings = candidate?.safetyRatings;
                }

                // 提取 token 使用情况
                if (parsedResponse.usageMetadata) {
                    responseData.usage = {
                        prompt_tokens: parsedResponse.usageMetadata.promptTokenCount,
                        completion_tokens: parsedResponse.usageMetadata.candidatesTokenCount,
                        total_tokens: parsedResponse.usageMetadata.totalTokenCount
                    };
                }

                // 提取错误信息
                if (parsedResponse.error) {
                    responseData.error = {
                        code: parsedResponse.error.code,
                        message: parsedResponse.error.message,
                        status: parsedResponse.error.status
                    };
                }

                // 保存完整响应（可选）
                if (process.env.TIGERHILL_SAVE_RAW === 'true') {
                    responseData.raw_response = parsedResponse;
                }
            } catch (e) {
                // 不是 JSON，保存原始文本
                responseData.raw_text = responseText.substring(0, 10000); // 限制大小
            }
        } catch (e) {
            console.error('[TigerHill] Failed to read response:', e);
            responseData.error_reading = e.message;
        }

        captureData.responses.push(responseData);
        saveCapture();

        console.log(`[TigerHill] Captured response (status: ${response.status}, ${responseData.usage?.total_tokens || 0} tokens)`);

        return response;
    } catch (err) {
        console.error('[TigerHill] Fetch error:', err);

        // 捕获错误
        const errorData = {
            request_id: requestId,
            timestamp: Date.now() / 1000,
            duration_ms: Date.now() - startTime,
            error: err.message,
            error_type: err.constructor.name,
            stack: err.stack
        };

        captureData.responses.push(errorData);
        saveCapture();

        throw err;
    }
};

// 辅助函数：从 contents 提取文本
function extractTextFromContents(contents) {
    if (!Array.isArray(contents)) {
        contents = [contents];
    }

    const texts = [];
    for (const content of contents) {
        if (content.parts) {
            const partTexts = extractTextFromParts(content.parts);
            if (partTexts.length > 0) {
                const role = content.role || 'unknown';
                texts.push(`[${role.toUpperCase()}]\n${partTexts.join('\n')}`);
            }
        }
    }
    return texts;
}

// 辅助函数：从 parts 提取文本
function extractTextFromParts(parts) {
    if (!parts || !Array.isArray(parts)) {
        return [];
    }

    return parts
        .filter(p => p.text)
        .map(p => p.text);
}

// 辅助函数：从 parts 提取工具调用
function extractToolCalls(parts) {
    if (!parts || !Array.isArray(parts)) {
        return [];
    }

    return parts
        .filter(p => p.functionCall)
        .map(p => ({
            name: p.functionCall.name,
            arguments: p.functionCall.args
        }));
}

// 保存捕获数据
function saveCapture() {
    try {
        captureData.end_time = Date.now() / 1000;
        captureData.duration = captureData.end_time - captureData.start_time;

        captureData.statistics = {
            total_requests: captureData.requests.length,
            total_responses: captureData.responses.length,
            total_tokens: captureData.responses.reduce((sum, r) => sum + (r.usage?.total_tokens || 0), 0)
        };

        fs.writeFileSync(CAPTURE_FILE, JSON.stringify(captureData, null, 2));
    } catch (error) {
        console.error('[TigerHill] Failed to save capture:', error);
    }
}

// 进程退出时保存
process.on('exit', () => {
    saveCapture();
    console.log(`[TigerHill] Final capture saved: ${CAPTURE_FILE}`);
    console.log(`[TigerHill] Captured ${captureData.requests.length} requests, ${captureData.responses.length} responses`);
});

process.on('SIGINT', () => {
    saveCapture();
    console.log(`\n[TigerHill] Capture saved on interrupt: ${CAPTURE_FILE}`);
    process.exit(0);
});

process.on('SIGTERM', () => {
    saveCapture();
    console.log(`[TigerHill] Capture saved on termination: ${CAPTURE_FILE}`);
    process.exit(0);
});

console.log('[TigerHill Fetch Interceptor] Ready to capture Gemini API calls via fetch()');
