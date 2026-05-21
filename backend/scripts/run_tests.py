#!/usr/bin/env python
"""
测试运行脚本
提供便捷的测试命令
"""

import argparse
import subprocess
import sys


def run_command(cmd: list[str], cwd: str = ".") -> int:
    """运行命令并返回退出码"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="KnowBase 测试运行器")
    parser.add_argument(
        "type",
        choices=["unit", "integration", "all", "coverage", "fast", "auth", "kb"],
        help="测试类型",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="详细输出",
    )
    parser.add_argument(
        "-x",
        "--exitfirst",
        action="store_true",
        help="遇到失败立即退出",
    )
    parser.add_argument(
        "-k",
        dest="keyword",
        help="只运行匹配关键字的测试",
    )

    args = parser.parse_args()

    # 基础命令
    cmd = ["pytest"]

    if args.verbose:
        cmd.append("-v")

    if args.exitfirst:
        cmd.append("-x")

    if args.keyword:
        cmd.extend(["-k", args.keyword])

    # 根据类型添加参数
    if args.type == "unit":
        cmd.extend(["tests/unit", "-m", "unit"])

    elif args.type == "integration":
        cmd.extend(["tests/", "--ignore=tests/unit", "-m", "integration"])

    elif args.type == "all":
        cmd.append("tests/")

    elif args.type == "coverage":
        cmd.extend(
            [
                "tests/",
                "--cov=app",
                "--cov-report=html",
                "--cov-report=term-missing",
            ]
        )

    elif args.type == "fast":
        cmd.extend(
            [
                "tests/unit",
                "-m",
                "unit and not slow",
                "-q",
            ]
        )

    elif args.type == "auth":
        cmd.extend(["tests/", "-m", "auth"])

    elif args.type == "kb":
        cmd.extend(["tests/", "-m", "kb"])

    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())
