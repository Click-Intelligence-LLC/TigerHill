// Go Agent 示例
//
// 一个简单的 Go 命令行 Agent
// 用于演示 TigerHill 如何测试 Go 语言的 Agent
//
// 编译:
//   go build -o go_agent go_agent.go
//
// 使用:
//   ./go_agent "你的提示"
//
// 测试:
//   python examples/cross_language/test_go_agent.py

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

// Response 表示 Agent 的响应
type Response struct {
	Output string `json:"output"`
	Status string `json:"status"`
}

func main() {
	// 检查参数
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "用法: %s <prompt>\n", os.Args[0])
		os.Exit(1)
	}

	// 获取提示
	prompt := os.Args[1]

	// 处理提示
	output := processPrompt(prompt)

	// 输出 JSON 响应
	response := Response{
		Output: output,
		Status: "success",
	}

	jsonOutput, err := json.Marshal(response)
	if err != nil {
		fmt.Fprintf(os.Stderr, "JSON 序列化失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Println(string(jsonOutput))
}

// processPrompt 处理用户提示
func processPrompt(prompt string) string {
	lowerPrompt := strings.ToLower(prompt)

	// 检查关键词并返回相应响应
	switch {
	case strings.Contains(lowerPrompt, "文件") || strings.Contains(lowerPrompt, "list"):
		return handleListFiles(prompt)

	case strings.Contains(lowerPrompt, "代码") || strings.Contains(lowerPrompt, "code"):
		return handleCodeGeneration(prompt)

	case strings.Contains(lowerPrompt, "分析") || strings.Contains(lowerPrompt, "analyze"):
		return handleAnalysis(prompt)

	case strings.Contains(lowerPrompt, "计算") || strings.Contains(lowerPrompt, "calculate"):
		return handleCalculation(prompt)

	default:
		return fmt.Sprintf("Go Agent 处理: %s", prompt)
	}
}

// handleListFiles 处理文件列表请求
func handleListFiles(prompt string) string {
	return `Go Agent 文件列表功能：
- main.go
- utils.go
- config.yaml
- README.md

这是一个模拟的文件列表。`
}

// handleCodeGeneration 处理代码生成请求
func handleCodeGeneration(prompt string) string {
	if strings.Contains(prompt, "Go") || strings.Contains(prompt, "go") {
		return `这是一个 Go 函数示例:

package main

import "fmt"

func add(a, b int) int {
    return a + b
}

func main() {
    result := add(5, 3)
    fmt.Println(result)  // 输出: 8
}`
	}

	return "我可以帮您生成 Go 代码。请在提示中包含 'Go'。"
}

// handleAnalysis 处理分析请求
func handleAnalysis(prompt string) string {
	return `Go Agent 分析结果：

1. 代码质量: 优秀
2. 性能评分: 85/100
3. 建议:
   - 添加错误处理
   - 增加单元测试
   - 优化算法复杂度

这是一个 Go Agent 提供的分析报告。`
}

// handleCalculation 处理计算请求
func handleCalculation(prompt string) string {
	return "Go Agent 计算器功能正在开发中。"
}
