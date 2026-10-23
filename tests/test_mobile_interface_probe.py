import ast
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mobile_interface_probe as probe


@contextmanager
def legacy_ast():
    original_parse = ast.parse
    source_function = getattr(ast, "get_source_segment", None)
    if source_function is not None:
        del ast.get_source_segment

    def parse_without_end_positions(*args, **kwargs):
        tree = original_parse(*args, **kwargs)
        for node in ast.walk(tree):
            for name in ("end_lineno", "end_col_offset"):
                if getattr(node, name, None) is not None:
                    delattr(node, name)
        return tree

    try:
        with mock.patch.object(ast, "parse", parse_without_end_positions):
            yield
    finally:
        if source_function is not None:
            ast.get_source_segment = source_function


class MobileInterfaceProbeTests(unittest.TestCase):
    def call_sites(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "process1.py"
            path.write_text(source, encoding="utf-8-sig")
            with legacy_ast():
                return probe._call_sites(path)

    def test_multiline_phone_and_ocr_calls_without_new_ast_interfaces(self):
        source = (
            "import xbot_visual\n"
            "from xbot_extensions import (\n"
            "    sample_ocr as offline_ocr,\n"
            ")\n"
            "def main():\n"
            "    result = xbot_visual.mobile.sample(\n"
            "        phone_device=phone_device,\n"
            "        text='中文与括号 )，保持完整',\n"
            "    )\n"
            "    result = offline_ocr.run(\n"
            "        image_path=image_path,\n"
            "    )\n"
        )
        entry = self.call_sites(source)
        self.assertEqual(entry["imports"], [
            "import xbot_visual",
            "from xbot_extensions import (\n    sample_ocr as offline_ocr,\n)",
        ])
        self.assertEqual([item["function"] for item in entry["calls"]],
                         ["xbot_visual.mobile.sample", "offline_ocr.run"])
        self.assertEqual(entry["calls"][0]["code"],
                         "".join(source.splitlines(True)[5:9]).rstrip("\n"))
        self.assertEqual(entry["calls"][1]["code"],
                         "".join(source.splitlines(True)[9:12]).rstrip("\n"))

    def test_inline_unicode_and_no_final_newline(self):
        source = "文字 = '中文'; phone_device.sample(text='中文')"
        entry = self.call_sites(source)
        self.assertEqual(entry["calls"][0]["code"], source)

    def test_explicit_line_continuation(self):
        source = "phone_device.sample(\\\n    text='中文',\\\n)\n"
        entry = self.call_sites(source)
        self.assertEqual(entry["calls"][0]["code"], source.rstrip("\n"))

    def test_collect_writes_report_without_touching_device(self):
        class Device:
            @property
            def page_source(self):
                raise AssertionError("不应读取设备属性")

            def sample(self):
                raise AssertionError("不应操作设备")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text(
                "import xbot_visual\nxbot_visual.mobile.sample(phone_device=phone_device)\n",
                encoding="utf-8",
            )
            with legacy_ast(), \
                    mock.patch.object(probe, "__file__", str(root / "mobile_interface_probe.py")), \
                    mock.patch.object(probe.tempfile, "gettempdir", return_value=directory):
                report_path = probe.collect(Device())
            report = json.loads(Path(report_path).read_text(encoding="utf-8"))
            self.assertEqual(report["source_errors"], [])
            self.assertEqual(report["device_api"]["page_source"]["kind"], "property")
            self.assertEqual(report["generated_calls"][0]["calls"][0]["function"],
                             "xbot_visual.mobile.sample")

    def test_current_flow_format_and_ocr_sources_are_collected(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            module_dir = app / "xbot_robot"
            module_dir.mkdir()
            extension = app / "xbot_extensions" / "activity_179ea575"
            extension.mkdir(parents=True)
            flow = '{"name":"子流程1","ocr":{"threshold":0.5}}'
            (module_dir / "process1.flow").write_text(flow, encoding="utf-8-sig")
            (app / "main.flow").write_text("主流程", encoding="utf-16")
            (extension / "process1.py").write_text("def main(args):\n    return args\n", encoding="utf-8")
            (extension / "package.json").write_text('{"name":"离线OCR"}', encoding="utf-8")
            data = app / "data"
            data.mkdir()
            (data / "task_cases.xlsx").write_text("PRIVATE_TASK", encoding="utf-8")
            report = {"source_errors": []}
            probe._project_sources(module_dir, report)
            self.assertEqual({p["file"] for p in report["flow_sources"]},
                             {"main.flow", "process1.flow"})
            self.assertIn(flow, [p["text"] for p in report["flow_sources"]])
            self.assertEqual({p["file"] for p in report["ocr_sources"]},
                             {"package.json", "process1.py"})
            self.assertNotIn("PRIVATE_TASK", json.dumps(report))
            self.assertEqual(report["source_errors"], [])

    def test_binary_flow_is_preserved(self):
        import base64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "process.flow"
            payload = b"\x00\xff\x01\x80flow"
            path.write_bytes(payload)
            entry = probe._source_file(path)
            self.assertEqual(entry["encoding"], "base64")
            self.assertEqual(base64.b64decode(entry["base64"]), payload)

    def test_loaded_element_class_is_described_without_instantiation(self):
        class MobileElement:
            def __init__(self):
                raise AssertionError("不应创建元素")

            @property
            def text(self):
                raise AssertionError("不应读取元素")

            def sample(self, value):
                raise AssertionError("不应操作元素")

        module = types.ModuleType("xbot.mobile.appium.element")
        module.MobileElement = MobileElement
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.dict(sys.modules, {module.__name__: module}), \
                mock.patch.object(probe, "__file__", str(Path(directory) / "probe.py")), \
                mock.patch.object(probe.tempfile, "gettempdir", return_value=directory):
            report = json.loads(Path(probe.collect(object())).read_text(encoding="utf-8"))
            api = report["element_api"][module.__name__ + ".MobileElement"]
            self.assertEqual(api["text"]["kind"], "property")
            self.assertEqual(api["sample"]["signature"], "(self, value)")


if __name__ == "__main__":
    unittest.main()
