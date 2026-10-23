"""Install instance support into the existing app; never replace task/config/state files."""
import argparse
import ast
import os
from pathlib import Path

VERSION = "1.2.0"
ROOT_FILES = ("core_runner.py", "lan_bridge.py", "mobile_instances.py")
MOBILE_FILES = ("mobile_locators.py", "mobile_adapter.py", "mobile_executor.py")
WEB_FILES = ("server.py", "index.html", "app.js", "style.css")


def patch_module(source, template):
    names = ("_device_bindings", "prepare_devices")
    original, target = ast.parse(source), ast.parse(template)
    old = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
    new = {n.name: n for n in target.body if isinstance(n, ast.FunctionDef)}
    if not set(names + ("start_execution", "read_task", "finish_device_error")).issubset(old):
        raise RuntimeError("现有module1缺少配套入口，尚未修改应用")
    lines, target_lines = source.splitlines(True), template.splitlines(True)
    for name in sorted(names, key=lambda n: old[n].lineno, reverse=True):
        before, after = old[name], new[name]
        lines[before.lineno - 1:before.end_lineno] = ["".join(target_lines[after.lineno - 1:after.end_lineno]).rstrip() + "\n"]
    result = "".join(lines)
    ast.parse(result)
    return result


def install(root, package):
    root, package = Path(root).resolve(), Path(package).resolve()
    for required in (root / "xbot_robot/module1.py", root / "core_runner.py", root / "data/task_cases.xlsx"):
        if not required.is_file():
            raise RuntimeError("缺少现有项目文件：" + str(required))
    values = {}
    for name in ROOT_FILES:
        values[root / name] = (package / name).read_bytes()
    for name in MOBILE_FILES:
        values[root / "xbot_robot" / name] = (package / name).read_bytes()
    for name in WEB_FILES:
        values[root / "lan_tool" / name] = (package / "lan_tool" / name).read_bytes()
    module = root / "xbot_robot/module1.py"
    values[module] = patch_module(module.read_text(encoding="utf-8-sig"),
                                  (package / "module1.py").read_text(encoding="utf-8-sig")).encode("utf-8")
    # Validate every Python candidate before the first write.
    for path, value in values.items():
        if path.suffix == ".py":
            ast.parse(value.decode("utf-8-sig"), filename=path.name)
    changed = []
    for path, data in values.items():
        if path.is_file() and path.read_bytes() == data:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".instances-tmp")
        try:
            temporary.write_bytes(data)
            os.replace(str(temporary), str(path))
        finally:
            if temporary.exists():
                temporary.unlink()
        changed.append(str(path.relative_to(root)))
    print("VERSION=" + VERSION)
    print("RESULT=" + ("INSTANCES_UPDATED" if changed else "ALREADY_CURRENT"))
    for name in changed:
        print("UPDATED=" + name)
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()
    install(args.root, args.package)
