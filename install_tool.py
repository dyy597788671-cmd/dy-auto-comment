"""Matched upgrade; preserve B's module prefix and all business data."""
import argparse
import ast
import os
from pathlib import Path

VERSION = '1.1.1'
FUNCTIONS = ('read_task', '_allocation_wait_seconds', 'prepare_interactions',
             '_device_bindings', 'start_execution', 'prepare_devices', 'finish_device_error')


def patch_module(source, template):
    original, target = ast.parse(source), ast.parse(template)
    existing = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
    updates = {n.name: n for n in target.body if isinstance(n, ast.FunctionDef)}
    required = {'read_task', 'prepare_devices', 'prepare_interactions',
                'record_action_result', 'finish_task', '_save_execution_error'}
    if not required.issubset(existing):
        raise RuntimeError('当前module1缺少已核对的接口，尚未修改项目。')
    source_lines, target_lines = source.splitlines(keepends=True), template.splitlines(keepends=True)
    replacements, additions = [], []
    for name in FUNCTIONS:
        fn = updates[name]
        body = ''.join(target_lines[fn.lineno - 1:fn.end_lineno]).rstrip() + '\n'
        if name in existing:
            old = existing[name]
            replacements.append((old.lineno - 1, old.end_lineno, body))
        else:
            additions.append(body)
    for begin, end, body in sorted(replacements, reverse=True):
        source_lines[begin:end] = [body]
    result = ''.join(source_lines)
    if additions:
        result = result.rstrip() + '\n\n\n' + '\n\n'.join(additions)
    ast.parse(result)
    return result


def candidates(root, package, web_only=False):
    root, package = Path(root).resolve(), Path(package).resolve()
    module = root / 'xbot_robot/module1.py'
    for path in (root / 'core_runner.py', module, root / 'data/task_cases.xlsx'):
        if not path.is_file():
            raise RuntimeError('缺少B项目文件：' + str(path))
    bridge = (package / 'lan_bridge.py').read_text(encoding='utf-8-sig')
    ast.parse(bridge)
    values = {root / 'lan_bridge.py': bridge.encode('utf-8')}
    if web_only:
        existing = {n.name for n in ast.parse(module.read_text(encoding='utf-8-sig')).body if isinstance(n, ast.FunctionDef)}
        if not {'start_execution', 'prepare_devices', 'finish_device_error'}.issubset(existing):
            raise RuntimeError('此设备数量修复需要已安装v1.1.0配套接口；尚未修改项目。')
    else:
        core = (package / 'core_runner.py').read_text(encoding='utf-8-sig')
        patched = patch_module(module.read_text(encoding='utf-8-sig'),
                               (package / 'module1.py').read_text(encoding='utf-8-sig'))
        ast.parse(core)
        ast.parse(patched)
        values.update({root / 'core_runner.py': core.encode('utf-8'), module: patched.encode('utf-8')})
    for path in sorted((package / 'lan_tool').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            values[root / 'lan_tool' / path.relative_to(package / 'lan_tool')] = path.read_bytes()
    return values


def install(root, package, check=False, web_only=False):
    values = candidates(root, package, web_only)
    changes = {p: data for p, data in values.items() if not p.is_file() or p.read_bytes() != data}
    if check:
        print('RESULT=' + ('UPDATE_REQUIRED' if changes else 'ALREADY_CURRENT'))
        return bool(changes)
    for path, data in changes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.install-tmp')
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
    print('VERSION=' + VERSION)
    print('RESULT=' + ('TOOL_UPDATED' if changes else 'ALREADY_CURRENT'))
    return bool(changes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--package', default=str(Path(__file__).parent))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--web-only', action='store_true')
    args = parser.parse_args()
    install(args.root, args.package, args.check, args.web_only)
