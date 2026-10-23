import ast
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
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


if __name__ == "__main__":
    unittest.main()
