import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorMessage,
  Input,
  Select,
  Spinner,
} from "@/components/ui";
import { useState } from "react";
import { Sparkles, Upload } from "lucide-react";

const buttonVariants: Array<{ label: string; variant?: Parameters<typeof Button>[0]["variant"] }> = [
  { label: "Primary", variant: "primary" },
  { label: "Secondary", variant: "secondary" },
  { label: "Outline", variant: "outline" },
  { label: "Ghost", variant: "ghost" },
  { label: "Destructive", variant: "destructive" },
];

export default function DesignSystemPreview() {
  const [search, setSearch] = useState("");

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text">设计系统预览</h1>
          <p className="text-text-muted">快速浏览可复用的基础组件和样式 tokens。</p>
        </div>
        <Badge variant="outline" className="uppercase tracking-wide">
          Phase 2 Ready
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Buttons</CardTitle>
          <CardDescription>不同语义的按钮状态</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          {buttonVariants.map(({ label, variant }) => (
            <Button key={label} variant={variant}>
              {label}
            </Button>
          ))}
          <Button variant="primary" leftIcon={<Upload className="h-4 w-4" />}>
            上传
          </Button>
          <Button variant="primary" rightIcon={<Sparkles className="h-4 w-4" />} isLoading>
            正在同步
          </Button>
          <Button variant="secondary" size="icon" aria-label="Loading state">
            <Spinner size="sm" className="text-brand-foreground" />
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>表单元素</CardTitle>
          <CardDescription>输入框与 Select 组件</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Input
              leadingIcon={<Sparkles className="h-4 w-4" />}
              placeholder="搜索会话..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Input
              type="email"
              placeholder="邮箱地址"
              trailingIcon={<Spinner size="sm" className="text-brand" />}
            />
          </div>
          <div className="space-y-3">
            <Select label="模型筛选">
              <option value="">全部模型</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              <option value="gpt-4o">GPT-4o</option>
            </Select>
            <Select label="状态" helperText="支持按状态过滤列表">
              <option value="">全部状态</option>
              <option value="success">成功</option>
              <option value="error">失败</option>
              <option value="timeout">超时</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>空状态</CardTitle>
            <CardDescription>用于列表或图表为空时的反馈</CardDescription>
          </CardHeader>
          <CardContent>
            <EmptyState
              action={<Button variant="primary">导入会话</Button>}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>错误提示</CardTitle>
            <CardDescription>标准化错误反馈</CardDescription>
          </CardHeader>
          <CardContent>
            <ErrorMessage
              title="数据导入失败"
              description="无法解析上传的 JSON 文件，请检查格式后重试。"
              actionLabel="重新导入"
              onAction={() => undefined}
              secondaryAction={<Button variant="outline">查看日志</Button>}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>信息卡片</CardTitle>
          <CardDescription>组合标题、描述与 footer 行为</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>本周会话</CardTitle>
              <CardDescription>过去 7 天导入的会话数量</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold text-text">128</p>
              <p className="text-sm text-status-success mt-2">+12.4% 环比增长</p>
            </CardContent>
            <CardFooter>
              <Button variant="ghost" size="sm">
                查看趋势
              </Button>
              <Badge variant="success">实时</Badge>
            </CardFooter>
          </Card>

          <Card className="shadow-card">
            <CardHeader>
              <CardTitle>平均响应时间</CardTitle>
              <CardDescription>包含所有模型的平均值</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold text-text">842ms</p>
              <p className="text-sm text-status-warning mt-2">+5.2% 环比上升</p>
            </CardContent>
            <CardFooter>
              <Button variant="ghost" size="sm">
                优化配置
              </Button>
              <Badge variant="warning">注意</Badge>
            </CardFooter>
          </Card>
        </CardContent>
      </Card>
    </div>
  );
}
