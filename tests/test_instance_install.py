import ast
from http.client import HTTPConnection
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install_instances
import lan_bridge
from lan_tool.server import ToolServer
from test_execution_output import temporary_root, prepare_root
from test_mobile_instances import roster, Shell


class InstallTests(unittest.TestCase):
    def test_update_preserves_state_config_uuid_and_unrelated_business_functions(self):
        package = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "xbot_robot").mkdir()
            (root / "data").mkdir()
            (root / "config").mkdir()
            originals = {
                "data/task_cases.xlsx": b"existing-excel",
                "data/runtime_state.json": b"existing-state",
                "data/lan_tool.sqlite3": b"existing-db",
                "config/settings.json": b"existing-config",
                "xbot_robot/package.json": b"existing-uuid-and-name",
            }
            for name, data in originals.items():
                (root / name).write_bytes(data)
            source = (package / "module1.py").read_text()
            source += "\ndef existing_custom_business():\n    return 'keep-me'\n"
            (root / "xbot_robot/module1.py").write_text(source)
            (root / "core_runner.py").write_text("old core")
            install_instances.install(root, package)
            for name, data in originals.items():
                self.assertEqual((root / name).read_bytes(), data)
            installed = (root / "xbot_robot/module1.py").read_text()
            before = {n.name: ast.dump(n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
            after = {n.name: ast.dump(n) for n in ast.parse(installed).body if isinstance(n, ast.FunctionDef)}
            for name in before.keys() - {"_device_bindings", "prepare_devices"}:
                self.assertEqual(before[name], after[name])
            self.assertEqual(install_instances.install(root, package), [])
            self.assertTrue((root / "mobile_instances.py").is_file())
            self.assertFalse(list(root.rglob("*.instances-tmp")))

    def test_invalid_source_is_rejected_before_any_file_write(self):
        package = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "xbot_robot").mkdir()
            (root / "data/task_cases.xlsx").write_bytes(b"keep")
            (root / "core_runner.py").write_bytes(b"keep-core")
            (root / "xbot_robot/module1.py").write_text("def other(): pass\n")
            with self.assertRaisesRegex(RuntimeError, "缺少配套入口"):
                install_instances.install(root, package)
            self.assertEqual((root / "core_runner.py").read_bytes(), b"keep-core")


class WebTests(unittest.TestCase):
    def test_http_context_shows_four_phones_seven_apps_and_submission_uses_seven(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, [])
            (root / "core_runner.py").write_text("# Existing installed core entry\n")
            shell = Shell()
            def run(phone, args):
                if phone == "usb-3" and args == ["pm", "list", "users"]:
                    return "UserInfo{0:主空间:c13} running"
                return shell(phone, args)
            roster(root, run, 4)
            with patch.object(lan_bridge, "_online_registered_devices", return_value={"usb-%d" % i for i in range(4)}) as online:
                server = ToolServer(("127.0.0.1", 0), root, "127.0.0.1")
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                client = HTTPConnection("127.0.0.1", server.server_port)
                try:
                    client.request("GET", "/api/context")
                    response = client.getresponse()
                    result = json.loads(response.read())
                    self.assertEqual(response.status, 200)
                    self.assertEqual(result["data"]["connected_device_count"], 7)
                    self.assertEqual(result["data"]["connected_physical_device_count"], 4)
                    self.assertEqual(online.call_count, 1)
                    values = {"keyword": "作品", "expected_author": "作者", "expected_douyin_id": "12345",
                              "content_type": "视频", "target_device_count": 7,
                              "comments": "\n".join("评论%d" % i for i in range(7))}
                    accepted = lan_bridge.submit(root, "browser", "127.0.0.1", values, return_details=True)
                    self.assertEqual(accepted["connected_device_count"], 7)
                    self.assertTrue(accepted["admitted"])
                    self.assertEqual(online.call_count, 2)
                    values["target_device_count"] = 8
                    values["comments"] = "一条"
                    with self.assertRaises(lan_bridge.core.EngineError) as error:
                        lan_bridge.submit(root, "browser", "127.0.0.1", values)
                    self.assertEqual(error.exception.code, "TARGET_COUNT_EXCEEDS_CONNECTED")
                    self.assertIn("7个", str(error.exception))
                finally:
                    client.close()
                    server.shutdown()
                    server.server_close()
                    thread.join()


if __name__ == "__main__":
    unittest.main()
