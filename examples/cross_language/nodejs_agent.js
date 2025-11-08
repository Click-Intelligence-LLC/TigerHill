/**
 * Node.js Agent 示例
 *
 * 一个简单的 Node.js Agent，提供 HTTP API 接口
 * 用于演示 TigerHill 如何测试非 Python 语言的 Agent
 *
 * 安装依赖:
 *   npm init -y
 *   npm install express
 *
 * 启动:
 *   node nodejs_agent.js
 */

const express = require('express');
const app = express();
const PORT = 3000;

// 中间件
app.use(express.json());

// 健康检查端点
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Agent 主接口
app.post('/api/agent', async (req, res) => {
    const { prompt } = req.body;

    if (!prompt) {
        return res.status(400).json({
            error: 'Missing prompt field',
            status: 'error'
        });
    }

    console.log(`[${new Date().toISOString()}] 收到提示: ${prompt}`);

    try {
        // Agent 处理逻辑
        const output = await processPrompt(prompt);

        res.json({
            output: output,
            status: 'success',
            timestamp: new Date().toISOString()
        });

        console.log(`[${new Date().toISOString()}] 响应: ${output.substring(0, 50)}...`);

    } catch (error) {
        console.error(`[${new Date().toISOString()}] 错误:`, error);

        res.status(500).json({
            error: error.message,
            status: 'error'
        });
    }
});

/**
 * Agent 核心处理函数
 * @param {string} prompt - 用户提示
 * @returns {Promise<string>} Agent 响应
 */
async function processPrompt(prompt) {
    // 模拟一些延迟
    await sleep(100);

    // 简单的规则匹配
    const lowerPrompt = prompt.toLowerCase();

    // 计算器功能
    if (lowerPrompt.includes('计算') || lowerPrompt.includes('加') ||
        lowerPrompt.includes('减') || lowerPrompt.includes('乘') ||
        lowerPrompt.includes('除')) {
        return handleCalculation(prompt);
    }

    // 质数相关
    if (lowerPrompt.includes('质数') || lowerPrompt.includes('prime')) {
        return handlePrimeNumber(prompt);
    }

    // 代码相关
    if (lowerPrompt.includes('代码') || lowerPrompt.includes('code') ||
        lowerPrompt.includes('函数') || lowerPrompt.includes('function')) {
        return handleCodeGeneration(prompt);
    }

    // 用户信息
    if (lowerPrompt.includes('用户') || lowerPrompt.includes('user')) {
        return handleUserInfo(prompt);
    }

    // 默认响应
    return `Node.js Agent 处理了您的提示: "${prompt}"`;
}

/**
 * 处理计算请求
 */
function handleCalculation(prompt) {
    // 尝试提取数学表达式
    const mathPattern = /(\d+)\s*([\+\-\*\/])\s*(\d+)/;
    const match = prompt.match(mathPattern);

    if (match) {
        const num1 = parseInt(match[1]);
        const operator = match[2];
        const num2 = parseInt(match[3]);

        let result;
        switch(operator) {
            case '+':
                result = num1 + num2;
                break;
            case '-':
                result = num1 - num2;
                break;
            case '*':
                result = num1 * num2;
                break;
            case '/':
                result = num1 / num2;
                break;
        }

        return `计算结果: ${num1} ${operator} ${num2} = ${result}`;
    }

    return '我可以帮您计算数学表达式，例如: 计算 6 + 7';
}

/**
 * 处理质数相关请求
 */
function handlePrimeNumber(prompt) {
    return `质数（prime number）是指在大于1的自然数中，除了1和它本身以外不再有其他因数的数。
例如: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29...

这是一个 Node.js Agent 的回答。`;
}

/**
 * 处理代码生成请求
 */
function handleCodeGeneration(prompt) {
    if (prompt.includes('Python') || prompt.includes('python')) {
        return `这是一个 Python 函数示例:

def add(a, b):
    """计算两数之和"""
    return a + b

# 使用示例
result = add(5, 3)
print(result)  # 输出: 8`;
    }

    if (prompt.includes('JavaScript') || prompt.includes('javascript')) {
        return `这是一个 JavaScript 函数示例:

function add(a, b) {
    // 计算两数之和
    return a + b;
}

// 使用示例
const result = add(5, 3);
console.log(result);  // 输出: 8`;
    }

    return '我可以帮您生成 Python 或 JavaScript 代码。请指定语言。';
}

/**
 * 处理用户信息请求
 */
function handleUserInfo(prompt) {
    return `用户信息查询功能。
这是一个模拟响应，实际应用中会从数据库获取真实用户数据。`;
}

/**
 * 睡眠函数
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 启动服务器
app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log(`Node.js Agent 已启动`);
    console.log(`监听端口: ${PORT}`);
    console.log(`健康检查: http://localhost:${PORT}/health`);
    console.log(`Agent API: http://localhost:${PORT}/api/agent`);
    console.log('='.repeat(60));
    console.log('\n可以使用 TigerHill 测试此 Agent:');
    console.log('  python examples/cross_language/test_nodejs_agent.py\n');
});

// 优雅关闭
process.on('SIGINT', () => {
    console.log('\n正在关闭服务器...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n正在关闭服务器...');
    process.exit(0);
});
