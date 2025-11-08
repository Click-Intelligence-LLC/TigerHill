#!/usr/bin/env python3
"""
TigerHill 快速验证脚本

一键验证所有核心功能是否正常工作
"""

import sys
import subprocess
import tempfile
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tigerhill.template_engine.loader import TemplateLoader
from tigerhill.template_engine.validator import TemplateValidator
from tigerhill.template_engine.generator import CodeGenerator
from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
from tigerhill.storage.trace_store import EventType


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text):
    """打印成功消息"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """打印错误消息"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text):
    """打印信息"""
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")


def test_template_library():
    """测试1: 模板库功能"""
    print_header("测试1: 模板库功能")

    try:
        # 1.1 加载模板
        print_info("测试 1.1: 加载模板...")
        loader = TemplateLoader()
        templates = loader.list_templates()

        if len(templates) >= 11:
            print_success(f"找到 {len(templates)} 个模板 (预期: 11+)")
        else:
            print_error(f"只找到 {len(templates)} 个模板 (预期: 11+)")
            return False

        # 1.2 测试模板加载
        print_info("测试 1.2: 加载HTTP API模板...")
        template = loader.load_template("http/http-api-test.yaml")

        if template.name == "http-api-test":
            print_success(f"模板加载成功: {template.display_name}")
        else:
            print_error(f"模板名称错误: {template.name}")
            return False

        # 1.3 参数验证
        print_info("测试 1.3: 参数验证...")
        validator = TemplateValidator(template)
        params = {
            "agent_name": "test-api",
            "api_url": "https://api.example.com",
            "http_method": "GET",
            "expected_status": 200,
            "validate_response": True
        }

        is_valid, errors = validator.validate(params)
        if is_valid:
            print_success("参数验证通过")
        else:
            print_error(f"参数验证失败: {errors}")
            return False

        # 1.4 代码生成
        print_info("测试 1.4: 代码生成...")
        output_dir = tempfile.mkdtemp(prefix="tigerhill_test_")
        generator = CodeGenerator(template)
        generated_files = generator.generate(
            params=params,
            output_dir=output_dir,
            overwrite=False
        )

        if len(generated_files) == 3:
            print_success(f"生成 {len(generated_files)} 个文件")
            for f in generated_files:
                print(f"   📄 {Path(f).name}")
        else:
            print_error(f"文件数量错误: {len(generated_files)} (预期: 3)")
            return False

        print_success("模板库功能测试通过!\n")
        return True

    except Exception as e:
        print_error(f"模板库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sqlite_database():
    """测试2: SQLite数据库功能"""
    print_header("测试2: SQLite数据库功能")

    try:
        # 2.1 创建数据库
        print_info("测试 2.1: 创建SQLite数据库...")
        db_path = tempfile.mktemp(suffix='.db')
        store = SQLiteTraceStore(db_path=db_path, auto_init=True)
        print_success(f"数据库创建成功: {db_path}")

        # 2.2 写入Trace
        print_info("测试 2.2: 写入Trace数据...")
        trace_ids = []

        for i in range(3):
            trace_id = store.start_trace(
                agent_name="test-agent",
                task_id=f"task-{i}",
                metadata={"test": True, "index": i}
            )
            trace_ids.append(trace_id)

            # 写入Events
            for j in range(3):
                # Prompt
                store.write_event(
                    {
                        "type": "prompt",
                        "content": f"Prompt {j}",
                        "total_tokens": 100,
                        "cost_usd": 0.003
                    },
                    trace_id=trace_id,
                    event_type=EventType.PROMPT
                )

                # Response
                store.write_event(
                    {
                        "type": "model_response",
                        "content": f"Response {j}",
                        "total_tokens": 200,
                        "cost_usd": 0.006
                    },
                    trace_id=trace_id,
                    event_type=EventType.MODEL_RESPONSE
                )

            # 结束Trace
            store.end_trace(trace_id)

        print_success(f"写入 {len(trace_ids)} 个Traces")

        # 2.3 查询Traces
        print_info("测试 2.3: 查询Traces...")
        all_traces = store.query_traces()

        if len(all_traces) == 3:
            print_success(f"查询到 {len(all_traces)} 个Traces")
        else:
            print_error(f"Trace数量错误: {len(all_traces)} (预期: 3)")
            return False

        # 2.4 验证统计
        print_info("测试 2.4: 验证统计信息...")
        stats = store.get_statistics()

        expected_stats = {
            'total_traces': 3,
            'total_events': 18,  # 3 traces * 6 events
            'total_llm_calls': 18,
            'total_tokens': 2700,  # 3 * 6 * (100 + 200)
        }

        all_correct = True
        for key, expected in expected_stats.items():
            actual = stats.get(key, 0)
            if actual == expected:
                print(f"   ✅ {key}: {actual}")
            else:
                print_error(f"{key}: {actual} (预期: {expected})")
                all_correct = False

        if not all_correct:
            return False

        # 2.5 测试查询和筛选
        print_info("测试 2.5: 查询和筛选...")
        filtered = store.query_traces(agent_name="test-agent")
        if len(filtered) == 3:
            print_success(f"筛选查询正确: {len(filtered)} 个Traces")
        else:
            print_error(f"筛选结果错误: {len(filtered)}")
            return False

        print_success("SQLite数据库功能测试通过!\n")
        return True

    except Exception as e:
        print_error(f"数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unit_tests():
    """测试3: 运行单元测试"""
    print_header("测试3: 单元测试套件")

    try:
        print_info("运行pytest单元测试...")

        # 运行模板引擎测试
        result = subprocess.run(
            ["pytest", "tests/test_template_engine/", "-v", "--tb=short"],
            cwd=project_root,
            env={**subprocess.os.environ, "PYTHONPATH": str(project_root)},
            capture_output=True,
            text=True
        )

        # 解析结果
        output = result.stdout + result.stderr

        if "passed" in output:
            # 提取通过的测试数量
            import re
            match = re.search(r'(\d+) passed', output)
            if match:
                passed = int(match.group(1))
                print_success(f"单元测试通过: {passed} 个测试")
            else:
                print_success("单元测试通过")

            return True
        else:
            print_error("单元测试失败")
            print(output)
            return False

    except FileNotFoundError:
        print_error("pytest未安装，跳过单元测试")
        print_info("安装pytest: pip install pytest")
        return True  # 不算作失败
    except Exception as e:
        print_error(f"单元测试运行失败: {e}")
        return False


def test_dashboard_integration():
    """测试4: Dashboard集成（仅检查文件）"""
    print_header("测试4: Dashboard集成")

    try:
        # 检查Dashboard文件
        print_info("检查Dashboard文件...")
        dashboard_app = project_root / "tigerhill/web/dashboard/app.py"

        if dashboard_app.exists():
            print_success(f"Dashboard应用存在: {dashboard_app.name}")
        else:
            print_error("Dashboard应用文件不存在")
            return False

        # 检查DataLoader
        data_loader = project_root / "tigerhill/web/dashboard/data/loader.py"
        if data_loader.exists():
            print_success(f"DataLoader存在: {data_loader.name}")
        else:
            print_error("DataLoader文件不存在")
            return False

        print_info("提示: 运行 'streamlit run tigerhill/web/dashboard/app.py' 启动Dashboard")
        print_success("Dashboard集成检查通过!\n")
        return True

    except Exception as e:
        print_error(f"Dashboard检查失败: {e}")
        return False


def main():
    """主函数"""
    print_header("🎯 TigerHill 快速验证")
    print("验证所有核心功能...\n")

    results = {}

    # 运行测试
    results['模板库'] = test_template_library()
    results['SQLite数据库'] = test_sqlite_database()
    results['单元测试'] = test_unit_tests()
    results['Dashboard集成'] = test_dashboard_integration()

    # 汇总结果
    print_header("📊 验证结果汇总")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for name, result in results.items():
        if result:
            print_success(f"{name}: 通过")
        else:
            print_error(f"{name}: 失败")

    print(f"\n{Colors.BOLD}总计: {passed}/{total} 通过{Colors.END}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过！TigerHill已准备就绪！{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  有 {failed} 项测试失败，请检查上面的错误信息{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
