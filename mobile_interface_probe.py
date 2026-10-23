"""采集当前影刀的真实调用接口；不查找元素、不操作手机、不导入新SDK。"""
import ast
import base64
import importlib.util
import inspect
import io
import json
from pathlib import Path
import sys
import tempfile
import tokenize


def _describe(value):
    try:
        signature = str(inspect.signature(value))
    except (TypeError, ValueError):
        signature = None
    return {"signature": signature, "doc": (inspect.getdoc(value) or "")[:4000]}


def _class_type_api(device_type):
    result = {}
    for cls in device_type.__mro__:
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


def _class_api(device):
    return _class_type_api(type(device))


def _source_file(path):
    """只读流程/扩展源码；二进制格式保留原始字节，不尝试执行。"""
    raw = path.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("单份流程源码超过8MiB：" + path.name)
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return {"file": path.name, "encoding": "utf-16", "text": raw.decode("utf-16")}
    try:
        text = raw.decode("utf-8-sig")
        if "\x00" not in text:
            return {"file": path.name, "encoding": "utf-8", "text": text}
    except UnicodeError:
        pass
    return {"file": path.name, "encoding": "base64",
            "base64": base64.b64encode(raw).decode("ascii")}


def _project_sources(module_dir, report):
    """兼容现有.flow工程；只读本应用流程及已知OCR扩展源码。"""
    flow_paths = set(module_dir.rglob("*.flow"))
    extension_roots = {module_dir / "xbot_extensions" / "activity_179ea575"}
    if module_dir.name == "xbot_robot":
        flow_paths.update(module_dir.parent.glob("*.flow"))
        extension_roots.add(module_dir.parent / "xbot_extensions" / "activity_179ea575")
    extension_package = sys.modules.get("xbot_extensions")
    if extension_package is not None:
        for path in vars(extension_package).get("__path__", ()):
            extension_roots.add(Path(path) / "activity_179ea575")
    for name, module in list(sys.modules.items()):
        if module is None or name != "xbot_extensions.activity_179ea575":
            continue
        module_path = vars(module).get("__file__")
        if module_path:
            extension_roots.add(Path(module_path).resolve().parent)
        for path in vars(module).get("__path__", ()):
            extension_roots.add(Path(path))

    ocr_paths = set()
    for root in extension_roots:
        if root.is_dir():
            ocr_paths.update(root.glob("*.py"))
            ocr_paths.update(root.glob("*.flow"))
            if (root / "package.json").is_file():
                ocr_paths.add(root / "package.json")
    report["source_layout"] = {
        "module_directory": str(module_dir),
        "module_code_files": sorted(path.name for path in module_dir.iterdir()
                                    if path.suffix in (".py", ".flow")),
        "ocr_directories_found": sorted(str(root) for root in extension_roots if root.is_dir()),
    }
    for key, paths in (("flow_sources", flow_paths), ("ocr_sources", ocr_paths)):
        report[key] = []
        for path in sorted(paths):
            try:
                report[key].append(_source_file(path))
            except (OSError, UnicodeError, ValueError) as error:
                report["source_errors"].append({"file": path.name, "error": str(error)})


def _statement_sources(source):
    """按逻辑语句保留源码，兼容没有AST结束位置的旧Python。"""
    lines = source.splitlines(True)
    statements = {}
    start = None
    ignored = (tokenize.INDENT, tokenize.DEDENT, tokenize.NL,
               tokenize.COMMENT, tokenize.ENCODING)
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.NEWLINE, tokenize.ENDMARKER):
            if start is not None:
                end = min(token.start[0], len(lines))
                code = "".join(lines[start - 1:end]).rstrip("\r\n")
                for line in range(start, end + 1):
                    statements[line] = code
                start = None
        elif start is None and token.type not in ignored:
            start = token.start[0]
    return statements


def _call_sites(path):
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=path.name)
    statements = _statement_sources(source)
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
            segment = statements.get(node.lineno, "")
            if "xbot" in (segment or ""):
                imports.append(segment)
        if not isinstance(node, ast.Call):
            continue
        name = dotted(node.func)
        root = name.split(".")[0]
        if (".mobile." in name or name.startswith(("phone_device.", "phone_devices[]"))
                or root in extensions or name == "xbot_visual.process.run"):
            calls.append({"line": node.lineno, "function": name,
                          "code": statements.get(node.lineno, "")})
    return {"file": path.name, "imports": imports, "calls": sorted(calls, key=lambda item: item["line"])}


def collect(phone_device):
    """在主流程连接完成后调用一次，返回本机接口报告文件完整路径。"""
    if phone_device is None:
        raise ValueError("传入已有phone_device，不能使用None")
    module_dir = Path(__file__).resolve().parent
    report = {
        "collector_version": 2,
        "python_version": sys.version,
        "device_class": type(phone_device).__module__ + "." + type(phone_device).__qualname__,
        "device_api": _class_api(phone_device),
        "loaded_mobile_api": {},
        "element_api": {},
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
            elif member == "MobileElement" and inspect.isclass(value):
                report["element_api"][name + "." + member] = _class_type_api(value)
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
    _project_sources(module_dir, report)
    try:
        report["lxml_available"] = importlib.util.find_spec("lxml") is not None
    except (ImportError, ValueError) as error:
        report["lxml_available"] = None
        report["source_errors"].append({"file": "lxml模块查询", "error": str(error)})
    report["collection_gaps"] = []
    if not report["generated_calls"] and not report["flow_sources"]:
        report["collection_gaps"].append("未取得手机操作所在流程源码")
    if not report["ocr_sources"]:
        report["collection_gaps"].append("未取得现有离线OCR扩展源码")
    path = Path(tempfile.gettempdir()) / "dy_mobile_interface.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("手机接口报告：" + str(path))
    print("流程源文件：" + str(len(report["flow_sources"]))
          + "；OCR源文件：" + str(len(report["ocr_sources"])))
    return str(path)

