"""采集当前影刀的真实调用接口；不查找元素、不操作手机、不导入新SDK。"""
import ast
import inspect
import json
from pathlib import Path
import sys
import tempfile


def _describe(value):
    try:
        signature = str(inspect.signature(value))
    except (TypeError, ValueError):
        signature = None
    return {"signature": signature, "doc": (inspect.getdoc(value) or "")[:4000]}


def _class_api(device):
    result = {}
    for cls in type(device).__mro__:
        for name, value in vars(cls).items():
            if name.startswith("_") or name in result:
                continue
            if isinstance(value, property):
                # 只读取描述符，不触发page_source等属性实际访问。
                result[name] = {"kind": "property", "doc": (value.__doc__ or "")[:4000]}
            elif isinstance(value, (staticmethod, classmethod)):
                result[name] = dict(_describe(value.__func__), kind=type(value).__name__)
            elif inspect.isroutine(value):
                result[name] = dict(_describe(value), kind="method")
    return result


def _call_sites(path):
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=path.name)
    extensions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("xbot_extensions"):
            extensions.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            extensions.update(alias.asname or alias.name.split(".")[0]
                              for alias in node.names if alias.name.startswith("xbot_extensions"))

    def dotted(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return dotted(node.value) + "." + node.attr
        if isinstance(node, ast.Subscript):
            return dotted(node.value) + "[]"
        return ""

    imports = []
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            segment = ast.get_source_segment(source, node)
            if "xbot" in (segment or ""):
                imports.append(segment)
        if not isinstance(node, ast.Call):
            continue
        name = dotted(node.func)
        root = name.split(".")[0]
        if (".mobile." in name or name.startswith(("phone_device.", "phone_devices[]"))
                or root in extensions or name == "xbot_visual.process.run"):
            calls.append({"line": node.lineno, "function": name,
                          "code": ast.get_source_segment(source, node)})
    return {"file": path.name, "imports": imports, "calls": sorted(calls, key=lambda item: item["line"])}


def collect(phone_device):
    """在主流程连接完成后调用一次，返回本机接口报告文件完整路径。"""
    if phone_device is None:
        raise ValueError("传入已有phone_device，不能使用None")
    module_dir = Path(__file__).resolve().parent
    report = {
        "python_version": sys.version,
        "device_class": type(phone_device).__module__ + "." + type(phone_device).__qualname__,
        "device_api": _class_api(phone_device),
        "loaded_mobile_api": {},
        "generated_calls": [],
        "source_errors": [],
    }
    # 只读已加载的真实手机模块，不猜接口名，不创建连接或新会话。
    for name, module in list(sys.modules.items()):
        if module is None or not (name.startswith("xbot.mobile") or name == "xbot_visual.mobile"):
            continue
        methods = {}
        for member, value in vars(module).items():
            if not member.startswith("_") and inspect.isfunction(value):
                methods[member] = _describe(value)
        if methods:
            report["loaded_mobile_api"][name] = methods
    # 当前应用生成的调用代码；不读取业务表、状态、数据库或账号文件。
    for path in sorted(module_dir.glob("*.py")):
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            entry = _call_sites(path)
            if entry["calls"]:
                report["generated_calls"].append(entry)
        except (OSError, UnicodeError, SyntaxError) as error:
            report["source_errors"].append({"file": path.name, "error": str(error)})
    path = Path(tempfile.gettempdir()) / "dy_mobile_interface.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("手机接口报告：" + str(path))
    return str(path)
