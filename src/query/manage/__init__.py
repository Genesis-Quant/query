"""独立查询包命令行入口；写库只由显式 workers 命令触发。"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "workers":
        from dotenv import load_dotenv

        load_dotenv(Path.cwd() / ".env")
        from .workers import main as run_workers

        return run_workers(arguments[1:], prog="query workers")
    parser = argparse.ArgumentParser(prog="query", description="编译查询 DOS 或更新因子窄表。")
    commands = parser.add_subparsers(dest="command", required=True)
    compile_parser = commands.add_parser("compile", help="编译可直接运行的会话脚本，不连接数据库")
    compile_parser.add_argument("--output", type=Path, help="输出 DOS 文件；省略时输出到 stdout")
    commands.add_parser("workers", help="更新因子窄表，使用 workers --help 查看选项")
    parsed = parser.parse_args(arguments)
    from query.database.compile.query.scripts import build_script

    script = build_script()
    if parsed.output is None:
        print(script, end="")
    else:
        parsed.output.parent.mkdir(parents=True, exist_ok=True)
        parsed.output.write_text(script, encoding="utf-8")
    return 0
