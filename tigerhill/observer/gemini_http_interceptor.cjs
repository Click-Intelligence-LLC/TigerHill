/**
 * TigerHill HTTP Interceptor for Gemini CLI
 *
 * 通过拦截 HTTPS 请求来捕获 Gemini API 的完整交互
 * 适用于已打包的应用（如 gemini-cli bundle）
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// 配置
const EXPORT_DIR = process.env.TIGERHILL_CAPTURE_PATH || path.resolve(process.cwd(), 'prompt_captures');
const GEMINI_API_HOSTS = [
    'generativelanguage.googleapis.com',
    'cloudcode-pa.googleapis.com',  // Gemini CLI uses this
    'aiplatform.googleapis.com',
    'content-aiplatform.googleapis.com'
];

/**
 * 提取 parts 中的纯文本
 * @param {Array} parts
 * @returns {string[]}
 */
function extractTextFromParts(parts) {
    if (!Array.isArray(parts)) {
        return [];
    }
    return parts
        .filter(part => typeof part === 'object' && typeof part.text === 'string')
        .map(part => part.text);
}

/**
 * 提取 contents 中的纯文本
 * @param {Array} contents
 * @returns {string[]}
 */
function extractTextFromContents(contents) {
    if (!Array.isArray(contents)) {
        return [];
    }
    return contents.flatMap(content => extractTextFromParts(content.parts));
}

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
        interceptor: 'http',
        version: '1.0'
    },
    requests: [],
    responses: []
};

console.log('[TigerHill HTTP Interceptor] Active');
console.log(`[TigerHill HTTP Interceptor] Capture file: ${CAPTURE_FILE}`);

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
        // 非 Gemini 请求，直接透传
        return originalHttpsRequest.apply(this, arguments);
    }

    console.log('[TigerHill] Intercepting Gemini API request');

    // 捕获请求数据
    let requestBody = '';
    const requestId = crypto.randomUUID();
    const requestTime = Date.now();

    // 创建代理请求对象
    const req = originalHttpsRequest(options, (res) => {
        let responseBody = '';

        // 捕获响应数据
        res.on('data', (chunk) => {
            responseBody += chunk.toString();
        });

        res.on('end', () => {
            try {
                // 解析并保存响应
                const responseData = {
                    request_id: requestId,
                    timestamp: Date.now() / 1000,
                    status_code: res.statusCode,
                    headers: res.headers
                };

                // 尝试解析 JSON 响应
                try {
                    const parsedResponse = JSON.parse(responseBody);

                    // 提取 Gemini 响应内容
                    if (parsedResponse.candidates) {
                        const candidate = parsedResponse.candidates[0];
                        if (candidate && candidate.content) {
                            const textParts = candidate.content.parts
                                .filter(p => p.text)
                                .map(p => p.text);
                            responseData.text = textParts.join('\n');
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

                    // 保存原始响应
                    responseData.raw_response = parsedResponse;
                } catch (e) {
                    // 如果不是 JSON，保存原始文本
                    responseData.raw_text = responseBody;
                }

                captureData.responses.push(responseData);

                // 立即写入文件
                saveCapture();

                console.log(`[TigerHill] Captured response (${responseBody.length} bytes)`);
            } catch (error) {
                console.error('[TigerHill] Failed to capture response:', error);
            }
        });

        // 调用原始回调
        if (callback) {
            callback(res);
        }
    });

    // Hook write 方法来捕获请求体
    const originalWrite = req.write.bind(req);
    req.write = function(chunk, encoding, callback) {
        if (chunk) {
            requestBody += chunk.toString();
        }
        return originalWrite(chunk, encoding, callback);
    };

    // Hook end 方法来保存完整请求
    const originalEnd = req.end.bind(req);
    req.end = function(chunk, encoding, callback) {
        if (chunk) {
            requestBody += chunk.toString();
        }

        try {
            // 解析并保存请求
            const requestData = {
                request_id: requestId,
                timestamp: requestTime / 1000,
                method: options.method || 'POST',
                url: `https://${options.hostname || options.host}${options.path || ''}`,
                headers: options.headers || {}
            };

            // 尝试解析请求体
            try {
                const parsedRequest = JSON.parse(requestBody);
                const requestPayload = parsedRequest.request || parsedRequest;

                // 提取模型信息
                if (parsedRequest.model) {
                    requestData.model = parsedRequest.model;
                }
                if (typeof options.path === 'string') {
                    const modelMatch = options.path.match(/models\/([\w-]+):/);
                    if (modelMatch) {
                        requestData.model = modelMatch[1];
                    }
                }

                // 提取 prompt
                if (requestPayload.contents) {
                    requestData.prompt = requestPayload.contents;

                    // 如果是简单文本，提取出来
                    const textParts = extractTextFromContents(requestPayload.contents);
                    if (textParts.length > 0) {
                        requestData.prompt_text = textParts.join('\n');
                    }
                }

                // 提取系统指令
                if (requestPayload.systemInstruction) {
                    requestData.system_instruction = requestPayload.systemInstruction;

                    // 提取文本形式
                    if (requestPayload.systemInstruction.parts) {
                        const systemTexts = extractTextFromParts(requestPayload.systemInstruction.parts);
                        requestData.system_prompt = systemTexts.join('\n');
                    }
                }

                // 提取生成配置
                if (requestPayload.generationConfig) {
                    requestData.generation_config = requestPayload.generationConfig;
                }

                // 提取工具配置
                if (requestPayload.tools) {
                    requestData.tools = requestPayload.tools;
                }

                // 提取安全设置
                if (requestPayload.safetySettings) {
                    requestData.safety_settings = requestPayload.safetySettings;
                }

                // 保存原始请求
                requestData.raw_request = parsedRequest;
            } catch (e) {
                // 如果不是 JSON，保存原始文本
                requestData.raw_body = requestBody;
            }

            captureData.requests.push(requestData);

            // 立即写入文件
            saveCapture();

            console.log(`[TigerHill] Captured request to ${requestData.model || 'unknown model'}`);
        } catch (error) {
            console.error('[TigerHill] Failed to capture request:', error);
        }

        return originalEnd(chunk, encoding, callback);
    };

    return req;
};

// 保存捕获数据
function saveCapture() {
    try {
        captureData.end_time = Date.now() / 1000;
        captureData.duration = captureData.end_time - captureData.start_time;

        captureData.statistics = {
            total_requests: captureData.requests.length,
            total_responses: captureData.responses.length
        };

        fs.writeFileSync(CAPTURE_FILE, JSON.stringify(captureData, null, 2));
    } catch (error) {
        console.error('[TigerHill] Failed to save capture:', error);
    }
}

// 进程退出时保存
process.on('exit', () => {
    saveCapture();
    console.log(`[TigerHill] Capture saved: ${CAPTURE_FILE}`);
});

process.on('SIGINT', () => {
    saveCapture();
    console.log(`[TigerHill] Capture saved: ${CAPTURE_FILE}`);
    process.exit();
});

console.log('[TigerHill HTTP Interceptor] Ready to capture Gemini API calls');
