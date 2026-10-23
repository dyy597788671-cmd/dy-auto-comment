import copy
from collections import deque
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mobile_executor import Executor, run


TASK = {"task_id": "task-1", "sender_account_id": "account-1", "physical_device_id": "phone-1",
        "run_token": "token-1", "keyword": "测试搜索", "expected_author": "作者",
        "expected_douyin_id": "author123", "content_type": "视频", "comment_content": "测试评论"}


class Snapshot:
    def __init__(self, candidates=()):
        self.values = list(candidates)

    def candidates(self, name):
        return self.values

    def node_signature(self):
        return ("node", (("稳定标题", "作者"),))


class Adapter:
    def __init__(self, events):
        self.events = events
        self.answers = {}
        self.snapshots = deque()
        self.back_error = None

    def exists(self, key, **kwargs):
        answer = self.answers.get(key)
        return answer.popleft() if answer else key == "L02"

    def click(self, key, **kwargs):
        self.events.append(("click", key))

    def click_xpath(self, expression):
        self.events.append(("cover", expression))

    def input_cursor(self, text):
        self.events.append(("input_cursor", text))

    def input_search(self, text):
        self.events.append(("input_search", text))

    def bounds(self, key):
        return (0, 100, 1080, 200)

    def nav_swipe(self, bounds, direction):
        self.events.append(("nav_swipe", direction))

    def results_swipe(self, bounds):
        self.events.append(("results_swipe",))

    def open_app(self):
        self.events.append(("open_app",))

    def back(self):
        self.events.append(("back",))
        if self.back_error:
            raise self.back_error

    def profile(self):
        self.events.append(("profile",))
        return "抖音号：author123", "作者"

    def snapshot(self):
        self.events.append(("snapshot",))
        return self.snapshots.popleft() if self.snapshots else Snapshot()

    def ocr_screen(self):
        self.events.append(("ocr",))
        return []

    def click_ocr(self, items, key):
        self.events.append(("click_ocr", key))


class Business:
    def __init__(self, events):
        self.events = events
        self.order = ["Like", "Comment", "Favorite", "Share"]
        self.verdicts = deque(["MATCH"])
        self.saved = []

    def prepare_interactions(self, task):
        self.events.append(("prepare",))
        return {"execution_order": self.order[:]}

    def record_action_result(self, actions, action, status, message, task_data):
        self.events.append(("record", action))
        self.saved = actions + [{"action": action, "status": status, "message": message}]
        return copy.deepcopy(self.saved)

    def verify_author(self, task, identity, name):
        self.events.append(("verify", identity, name))
        return self.verdicts.popleft()

    def finish_task(self, task, actions, status, log_message):
        self.events.append(("finish", status, log_message))
        return {"status": status, "executed_actions": copy.deepcopy(actions), "log_message": log_message}


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.adapter = Adapter(self.events)
        self.business = Business(self.events)
        self.executor = Executor(self.adapter, self.business, sleep=lambda seconds: None,
                                 uniform=lambda low, high: low)

    def test_video_comment_saves_before_back(self):
        self.executor.video_comment(TASK)
        self.assertEqual(self.events, [("click", "L21"), ("click", "L22"),
                                      ("input_cursor", "测试评论"), ("click", "L23"),
                                      ("record", "Comment"), ("back",)])

    def test_failed_back_does_not_lose_sent_comment(self):
        self.adapter.back_error = RuntimeError("后退失败")
        with self.assertRaisesRegex(RuntimeError, "后退失败"):
            self.executor.video_comment(TASK)
        self.assertEqual(self.business.saved[0]["action"], "Comment")

    def test_photo_comment_reuses_cursor_without_input_click_or_back(self):
        self.adapter.answers["L24"] = deque([True, False, False])
        self.executor.photo_comment(dict(TASK, content_type="图文"))
        self.assertEqual(self.events, [("click", "L24"), ("click", "L24"),
                                      ("input_cursor", "测试评论"), ("click", "L23"),
                                      ("record", "Comment")])

    def test_photo_comment_stops_after_three_clicks(self):
        self.adapter.answers["L24"] = deque([True, True, True])
        with self.assertRaisesRegex(RuntimeError, "已点击3次"):
            self.executor.photo_comment(TASK)
        self.assertEqual(self.events, [("click", "L24")] * 3)
        self.assertEqual(self.business.saved, [])

    def test_each_navigation_direction_has_six_swipes(self):
        for section, first, second in (("视频", "left", "right"), ("综合", "right", "left")):
            self.events.clear()
            with self.assertRaisesRegex(RuntimeError, "未找到搜索栏目"):
                self.executor.switch_section(section, (0, 100, 1080, 200))
            self.assertEqual(self.events, [("nav_swipe", first)] * 6 + [("nav_swipe", second)] * 6)

    def test_navigation_finds_target_on_last_allowed_swipe(self):
        self.adapter.answers["L07"] = deque([False] * 12 + [True])
        self.executor.switch_section("图文", (0, 100, 1080, 200))
        self.assertEqual(len([e for e in self.events if e[0] == "nav_swipe"]), 12)
        self.assertEqual(self.events[-1], ("click", "L07"))

    def test_author_return_counts(self):
        for verdict, backs in (("MATCH", 1), ("MISMATCH", 2), ("UNCERTAIN", 1)):
            self.events.clear()
            self.business.verdicts = deque([verdict])
            if verdict == "UNCERTAIN":
                with self.assertRaisesRegex(RuntimeError, "核验不确定"):
                    self.executor.verify_candidate(TASK, 1)
            else:
                self.assertEqual(self.executor.verify_candidate(TASK, 1), verdict)
            self.assertEqual(self.events.count(("back",)), backs)

    def test_resume_only_completes_remaining_order(self):
        saved = [{"action": "Like", "status": "PASSED", "message": ""},
                 {"action": "Comment", "status": "PASSED", "message": ""}]
        task = dict(TASK, action_results=saved)
        self.business.order = ["Favorite"]
        with mock.patch.object(self.executor, "find_work", return_value=(True, False)):
            result = self.executor.execute(task)
        self.assertEqual([item["action"] for item in result["executed_actions"]],
                         ["Like", "Comment", "Favorite"])
        self.assertNotIn(("click", "L19"), self.events)
        self.assertNotIn(("click", "L21"), self.events)
        self.assertNotIn(("click", "L27"), self.events)
        self.assertEqual(self.events.count(("open_app",)), 1)
        self.assertEqual(self.events.count(("back",)), 0)

    def test_share_uses_saved_plan_and_first_friend_rule(self):
        self.business.order = ["Like", "Favorite", "Share"]
        self.executor.interact(TASK)
        self.assertEqual([e for e in self.events if e[0] == "record"],
                         [("record", "Like"), ("record", "Favorite"), ("record", "Share")])
        self.assertIn(("click", "L29"), self.events)
        self.assertIn(("click_ocr", "L30"), self.events)
        self.assertNotIn(("back",), self.events)

    def test_not_found_keeps_mismatch_across_sections_and_refreshes_snapshot(self):
        self.adapter.answers["L07"] = deque([True, True])
        self.adapter.snapshots.append(Snapshot([1]))
        self.business.verdicts = deque(["MISMATCH"])
        result = self.executor.execute(TASK)
        self.assertEqual(result["status"], "NOT_FOUND")
        self.assertEqual(result["log_message"], "抖音号不同")
        self.assertEqual(self.events.count(("ocr",)), 2)  # 两个筛选面板，结果签名使用节点。
        self.assertEqual(self.events.count(("results_swipe",)), 6)
        cover_index = next(i for i, e in enumerate(self.events) if e[0] == "cover")
        second_back = next(i for i in range(cover_index + 1, len(self.events))
                           if self.events[i] == ("back",) and self.events[i - 1] == ("back",))
        self.assertEqual(self.events[second_back + 1], ("snapshot",))

    def test_run_error_keeps_original_message_and_bound_task(self):
        business = mock.Mock()
        business.read_task.return_value = dict(TASK)
        business.finish_device_error.return_value = {"released": True}
        identity = {"sender_account_id": "account-1", "device_id": "phone-1", "task_id": "task-1", "android_user_id": 0, "package_name": "com.ss.android.ugc.aweme"}
        with mock.patch("mobile_executor.importlib.import_module", return_value=business), \
                mock.patch.object(Executor, "execute", side_effect=RuntimeError("原始手机异常")):
            result = run(object(), identity)
        self.assertEqual(result["status"], "FAILED")
        business.finish_device_error.assert_called_once_with("account-1", "phone-1", "原始手机异常", "task-1")

    def test_unreleased_error_reaches_existing_main_catch(self):
        business = mock.Mock()
        business.read_task.side_effect = RuntimeError("原始读取异常")
        business.finish_device_error.return_value = {"released": False}
        identity = {"sender_account_id": "account-1", "device_id": "phone-1", "task_id": "task-1", "android_user_id": 0, "package_name": "com.ss.android.ugc.aweme"}
        with mock.patch("mobile_executor.importlib.import_module", return_value=business):
            with self.assertRaisesRegex(RuntimeError, "原始读取异常"):
                run(object(), identity)


if __name__ == "__main__":
    unittest.main()
