/**
 * TigerHill Node.js Observer
 *
 * 为 Node.js 的 Google Generative AI SDK 提供 instrumentation。
 *
 * 使用方式：
 * 1. 显式包装：
 *    const { wrapGenerativeModel } = require('tigerhill-observer');
 *    const WrappedModel = wrapGenerativeModel(GoogleGenerativeAI);
 *
 * 2. 自动注入（通过 shim）：
 *    NODE_OPTIONS="--require ./tigerhill-shim.js" node script.js
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

/**
 * 包装 GoogleGenerativeAI 模型
 *
 * @param {Object} ModelClass - GoogleGenerativeAI 类或实例
 * @param {Object} options - 配置选项
 * @param {Function} options.onRequest - 请求捕获回调
 * @param {Function} options.onResponse - 响应捕获回调
 * @param {string} options.captureEndpoint - TigerHill 捕获服务端点
 * @param {boolean} options.autoExport - 是否自动导出到文件
 * @param {string} options.exportPath - 导出路径
 * @returns {Object} 包装后的模型类
 */
function wrapGenerativeModel(ModelClass, options = {}) {
    const {
        onRequest,
        onResponse,
        captureEndpoint = null,
        autoExport = true,
        exportPath = './prompt_captures'
    } = options;

    // 如果是类，包装其原型方法
    if (typeof ModelClass === 'function') {
        return wrapModelClass(ModelClass, options);
    }

    // 如果是实例，直接包装
    return wrapModelInstance(ModelClass, options);
}

/**
 * 包装模型类
 */
function wrapModelClass(ModelClass, options) {
    const { onRequest, onResponse, captureEndpoint, autoExport, exportPath } = options;

    class WrappedGenerativeModel extends ModelClass {
        constructor(...args) {
            super(...args);

            this._tigerhillOptions = options;
            this._tigerhillCaptureId = generateCaptureId();
            this._tigerhillCaptures = [];

            console.log(`[TigerHill] Wrapped model: ${this.model || 'unknown'}`);
        }

        async generateContent(request) {
            // 捕获请求
            const requestData = this._extractRequestData(request);
            await this._captureRequest(requestData);

            // 执行原始方法
            const startTime = Date.now();
            let response;
            let error = null;

            try {
                response = await super.generateContent(request);
            } catch (err) {
                error = err;
                throw err;
            } finally {
                const duration = Date.now() - startTime;

                // 捕获响应或错误
                if (error) {
                    await this._captureError(error, duration);
                } else {
                    const responseData = this._extractResponseData(response);
                    responseData.duration_ms = duration;
                    await this._captureResponse(responseData);
                }
            }

            return response;
        }

        async *generateContentStream(request) {
            // 捕获请求
            const requestData = this._extractRequestData(request);
            await this._captureRequest(requestData);

            // 执行原始方法
            const startTime = Date.now();
            const chunks = [];

            try {
                for await (const chunk of super.generateContentStream(request)) {
                    chunks.push(chunk);
                    yield chunk;
                }

                // 捕获完整响应
                const duration = Date.now() - startTime;
                const responseData = this._extractStreamResponseData(chunks);
                responseData.duration_ms = duration;
                await this._captureResponse(responseData);

            } catch (error) {
                const duration = Date.now() - startTime;
                await this._captureError(error, duration);
                throw error;
            }
        }

        /**
         * 提取请求数据
         */
        _extractRequestData(request) {
            const data = {
                timestamp: Date.now(),
                model: this.model || 'unknown',
                request_type: 'generate_content'
            };

            // 提取 prompt
            if (typeof request === 'string') {
                data.prompt = request;
            } else if (request.contents) {
                data.prompt = request.contents;
            } else {
                data.prompt = JSON.stringify(request);
            }

            // 提取生成配置
            if (request.generationConfig) {
                data.generation_config = request.generationConfig;
            }

            // 提取工具
            if (request.tools) {
                data.tools = request.tools.map(tool => ({
                    name: tool.functionDeclarations?.[0]?.name || 'unknown',
                    description: tool.functionDeclarations?.[0]?.description,
                    parameters: tool.functionDeclarations?.[0]?.parameters
                }));
            }

            // 提取系统指令
            if (request.systemInstruction) {
                data.system_prompt = request.systemInstruction;
            }

            // 提取安全设置
            if (request.safetySettings) {
                data.safety_settings = request.safetySettings;
            }

            return data;
        }

        /**
         * 提取响应数据
         */
        _extractResponseData(response) {
            const data = {
                timestamp: Date.now()
            };

            try {
                // 提取文本
                if (response.response) {
                    data.text = response.response.text();

                    // 提取候选项
                    if (response.response.candidates) {
                        data.candidates = response.response.candidates.map(c => ({
                            text: c.content?.parts?.map(p => p.text).join(''),
                            finishReason: c.finishReason,
                            safetyRatings: c.safetyRatings
                        }));

                        data.finish_reason = data.candidates[0]?.finishReason;
                    }

                    // 提取 token 使用情况
                    if (response.response.usageMetadata) {
                        data.usage = {
                            prompt_tokens: response.response.usageMetadata.promptTokenCount,
                            completion_tokens: response.response.usageMetadata.candidatesTokenCount,
                            total_tokens: response.response.usageMetadata.totalTokenCount
                        };
                    }

                    // 提取工具调用
                    const toolCalls = this._extractToolCalls(response.response);
                    if (toolCalls.length > 0) {
                        data.tool_calls = toolCalls;
                    }
                }
            } catch (error) {
                console.error('[TigerHill] Failed to extract response data:', error);
                data.text = String(response);
            }

            return data;
        }

        /**
         * 提取流式响应数据
         */
        _extractStreamResponseData(chunks) {
            const data = {
                timestamp: Date.now(),
                text: '',
                chunks_count: chunks.length
            };

            try {
                // 合并所有 chunks
                const texts = chunks.map(chunk => {
                    if (chunk.text) return chunk.text();
                    if (chunk.response) return chunk.response.text();
                    return '';
                });
                data.text = texts.join('');

                // 使用最后一个 chunk 的元数据
                const lastChunk = chunks[chunks.length - 1];
                if (lastChunk.response?.usageMetadata) {
                    data.usage = {
                        prompt_tokens: lastChunk.response.usageMetadata.promptTokenCount,
                        completion_tokens: lastChunk.response.usageMetadata.candidatesTokenCount,
                        total_tokens: lastChunk.response.usageMetadata.totalTokenCount
                    };
                }
            } catch (error) {
                console.error('[TigerHill] Failed to extract stream response data:', error);
            }

            return data;
        }

        /**
         * 提取工具调用
         */
        _extractToolCalls(response) {
            const toolCalls = [];

            try {
                if (response.candidates) {
                    for (const candidate of response.candidates) {
                        if (candidate.content?.parts) {
                            for (const part of candidate.content.parts) {
                                if (part.functionCall) {
                                    toolCalls.push({
                                        name: part.functionCall.name,
                                        arguments: part.functionCall.args
                                    });
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('[TigerHill] Failed to extract tool calls:', error);
            }

            return toolCalls;
        }

        /**
         * 捕获请求
         */
        async _captureRequest(data) {
            this._tigerhillCaptures.push({ type: 'request', data });

            // 调用回调
            if (this._tigerhillOptions.onRequest) {
                try {
                    await this._tigerhillOptions.onRequest(data);
                } catch (error) {
                    console.error('[TigerHill] Request callback failed:', error);
                }
            }

            // 发送到端点
            if (this._tigerhillOptions.captureEndpoint) {
                await this._sendToEndpoint('request', data);
            }
        }

        /**
         * 捕获响应
         */
        async _captureResponse(data) {
            this._tigerhillCaptures.push({ type: 'response', data });

            // 调用回调
            if (this._tigerhillOptions.onResponse) {
                try {
                    await this._tigerhillOptions.onResponse(data);
                } catch (error) {
                    console.error('[TigerHill] Response callback failed:', error);
                }
            }

            // 发送到端点
            if (this._tigerhillOptions.captureEndpoint) {
                await this._sendToEndpoint('response', data);
            }

            // 自动导出
            if (this._tigerhillOptions.autoExport) {
                await this._exportCaptures();
            }
        }

        /**
         * 捕获错误
         */
        async _captureError(error, duration) {
            const errorData = {
                timestamp: Date.now(),
                error: error.message,
                stack: error.stack,
                duration_ms: duration
            };

            this._tigerhillCaptures.push({ type: 'error', data: errorData });

            if (this._tigerhillOptions.autoExport) {
                await this._exportCaptures();
            }
        }

        /**
         * 发送到端点
         */
        async _sendToEndpoint(type, data) {
            const endpoint = this._tigerhillOptions.captureEndpoint;
            const payload = JSON.stringify({
                capture_id: this._tigerhillCaptureId,
                type,
                data
            });

            return new Promise((resolve) => {
                const url = new URL(endpoint);
                const client = url.protocol === 'https:' ? https : http;

                const req = client.request({
                    hostname: url.hostname,
                    port: url.port,
                    path: url.pathname,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(payload)
                    }
                }, (res) => {
                    resolve();
                });

                req.on('error', (error) => {
                    console.error('[TigerHill] Failed to send to endpoint:', error);
                    resolve();
                });

                req.write(payload);
                req.end();
            });
        }

        /**
         * 导出捕获数据
         */
        async _exportCaptures() {
            try {
                const exportDir = this._tigerhillOptions.exportPath || './prompt_captures';

                // 确保目录存在
                if (!fs.existsSync(exportDir)) {
                    fs.mkdirSync(exportDir, { recursive: true });
                }

                const filename = `capture_${this._tigerhillCaptureId}_${Date.now()}.json`;
                const filepath = path.join(exportDir, filename);

                const captureData = {
                    capture_id: this._tigerhillCaptureId,
                    model: this.model,
                    timestamp: Date.now(),
                    captures: this._tigerhillCaptures
                };

                fs.writeFileSync(filepath, JSON.stringify(captureData, null, 2));
                console.log(`[TigerHill] Exported captures to: ${filepath}`);
            } catch (error) {
                console.error('[TigerHill] Failed to export captures:', error);
            }
        }
    }

    return WrappedGenerativeModel;
}

/**
 * 包装模型实例
 */
function wrapModelInstance(modelInstance, options) {
    // TODO: 实现实例包装
    console.warn('[TigerHill] Instance wrapping not yet implemented');
    return modelInstance;
}

/**
 * 生成捕获 ID
 */
function generateCaptureId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 创建 shim 文件
 */
function createShim(outputPath = './tigerhill-shim.js') {
    const shimContent = `
// TigerHill Auto-Instrumentation Shim
// 自动包装 @google/generative-ai

const Module = require('module');
const originalRequire = Module.prototype.require;
const { wrapGenerativeModel } = require('${__filename}');

Module.prototype.require = function(id) {
    const module = originalRequire.apply(this, arguments);

    if (id === '@google/generative-ai') {
        console.log('[TigerHill] Auto-instrumenting @google/generative-ai');

        const { GoogleGenerativeAI } = module;

        // 包装构造函数
        module.GoogleGenerativeAI = new Proxy(GoogleGenerativeAI, {
            construct(target, args) {
                const instance = new target(...args);

                // 包装 getGenerativeModel
                const originalGetModel = instance.getGenerativeModel.bind(instance);
                instance.getGenerativeModel = function(...modelArgs) {
                    const model = originalGetModel(...modelArgs);
                    const WrappedModel = wrapGenerativeModel(model.constructor, {
                        autoExport: true,
                        exportPath: process.env.TIGERHILL_CAPTURE_PATH || './prompt_captures'
                    });
                    return new WrappedModel(model.model);
                };

                return instance;
            }
        });
    }

    return module;
};

console.log('[TigerHill] Shim loaded. Set TIGERHILL_CAPTURE_PATH to customize output directory.');
`;

    fs.writeFileSync(outputPath, shimContent);
    console.log(`[TigerHill] Created shim file: ${outputPath}`);
    console.log(`[TigerHill] Usage: NODE_OPTIONS="--require ${outputPath}" node your_script.js`);
}

module.exports = {
    wrapGenerativeModel,
    createShim
};
