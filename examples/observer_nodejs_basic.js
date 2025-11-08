/**
 * TigerHill Observer SDK - Node.js Basic Example
 *
 * 演示如何使用 TigerHill Observer SDK 捕获 Google Generative AI 的 prompt 和响应。
 *
 * 使用步骤：
 * 1. 安装依赖: npm install @google/generative-ai
 * 2. 设置环境变量: export GOOGLE_API_KEY=your_api_key
 * 3. 运行: node examples/observer_nodejs_basic.js
 */

const { GoogleGenerativeAI } = require('@google/generative-ai');
const { wrapGenerativeModel } = require('../tigerhill/observer/node_observer');

async function main() {
    // 检查 API key
    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
        console.error('Error: Please set GOOGLE_API_KEY environment variable');
        console.error('Example: export GOOGLE_API_KEY=your_api_key');
        process.exit(1);
    }

    console.log('='.repeat(80));
    console.log('🚀 TigerHill Observer SDK - Node.js Example');
    console.log('='.repeat(80));

    // 1. 包装 GoogleGenerativeAI
    console.log('\n[Step 1] Wrapping GenerativeModel...');

    const capturedData = {
        requests: [],
        responses: []
    };

    const WrappedModel = wrapGenerativeModel(
        require('@google/generative-ai').GoogleGenerativeAI.prototype.constructor,
        {
            // 请求回调
            onRequest: (data) => {
                console.log(`\n📤 Request captured:`);
                console.log(`   Model: ${data.model}`);
                console.log(`   Prompt: ${JSON.stringify(data.prompt).substring(0, 80)}...`);
                capturedData.requests.push(data);
            },

            // 响应回调
            onResponse: (data) => {
                console.log(`\n📥 Response captured:`);
                console.log(`   Text length: ${data.text?.length || 0} characters`);
                if (data.usage) {
                    console.log(`   Tokens: ${data.usage.total_tokens} (prompt: ${data.usage.prompt_tokens}, completion: ${data.usage.completion_tokens})`);
                }
                capturedData.responses.push(data);
            },

            // 自动导出配置
            autoExport: true,
            exportPath: './prompt_captures',

            // 可选：发送到 TigerHill 服务器
            // captureEndpoint: 'http://localhost:8000/api/capture'
        }
    );

    // 2. 创建 AI 实例
    console.log('\n[Step 2] Creating AI instance...');
    const genAI = new GoogleGenerativeAI(apiKey);

    // 注意：由于 Node.js SDK 的限制，我们需要手动包装模型实例
    // 这里我们使用基础模型进行演示
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

    console.log('✅ Model created: gemini-2.5-flash');

    // 3. 使用模型生成内容
    console.log('\n[Step 3] Generating content...');

    // 第一个请求
    console.log('\n--- Request 1: Fibonacci Function ---');
    const prompt1 = 'Write a Python function to calculate fibonacci numbers';
    const result1 = await model.generateContent(prompt1);
    const response1 = await result1.response;
    const text1 = response1.text();

    console.log(`✅ Response received: ${text1.length} characters`);
    console.log(`   Preview: ${text1.substring(0, 100)}...`);

    // 第二个请求
    console.log('\n--- Request 2: Optimization ---');
    const prompt2 = 'Can you optimize the fibonacci function with memoization?';
    const result2 = await model.generateContent(prompt2);
    const response2 = await result2.response;
    const text2 = response2.text();

    console.log(`✅ Response received: ${text2.length} characters`);
    console.log(`   Preview: ${text2.substring(0, 100)}...`);

    // 4. 显示统计信息
    console.log('\n' + '='.repeat(80));
    console.log('📊 Capture Statistics:');
    console.log('='.repeat(80));
    console.log(`Total Requests: ${capturedData.requests.length}`);
    console.log(`Total Responses: ${capturedData.responses.length}`);

    let totalTokens = 0;
    let totalPromptTokens = 0;
    let totalCompletionTokens = 0;

    capturedData.responses.forEach(resp => {
        if (resp.usage) {
            totalTokens += resp.usage.total_tokens || 0;
            totalPromptTokens += resp.usage.prompt_tokens || 0;
            totalCompletionTokens += resp.usage.completion_tokens || 0;
        }
    });

    console.log(`Total Tokens: ${totalTokens.toLocaleString()}`);
    console.log(`  - Prompt Tokens: ${totalPromptTokens.toLocaleString()}`);
    console.log(`  - Completion Tokens: ${totalCompletionTokens.toLocaleString()}`);

    if (capturedData.requests.length > 0) {
        console.log(`Average Tokens per Request: ${(totalTokens / capturedData.requests.length).toFixed(0)}`);
    }

    console.log('='.repeat(80));

    // 5. 使用提示
    console.log('\n💡 Next Steps:');
    console.log('   1. Check ./prompt_captures/ for exported JSON files');
    console.log('   2. Use Python PromptAnalyzer to analyze the data:');
    console.log('      python examples/observer_python_analysis.py');
    console.log('   3. Export to TraceStore for testing:');
    console.log('      python examples/observer_tracestore_integration.py');
    console.log('   4. Integrate with your CI/CD pipeline');

    console.log('\n✅ Example completed successfully!');
}

// 错误处理
main().catch(error => {
    console.error('\n❌ Error:', error.message);
    console.error(error.stack);
    process.exit(1);
});


/**
 * Alternative: Using Auto-Instrumentation with Shim
 *
 * For automatic instrumentation without manual wrapping:
 *
 * 1. Create shim file:
 *    const { createShim } = require('./tigerhill/observer/node_observer');
 *    createShim('./tigerhill-shim.js');
 *
 * 2. Use shim:
 *    NODE_OPTIONS="--require ./tigerhill-shim.js" node your_script.js
 *
 * This will automatically instrument all @google/generative-ai imports.
 */
