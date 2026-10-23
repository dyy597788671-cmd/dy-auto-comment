from collections import deque
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mobile_adapter import MobileAdapter, ResultSnapshot, ScanState, ocr_signature, check_environment
import mobile_locators as loc


def native_card(title, name, timestamp="1小时前", likes="9"):
    card = etree.XML('''<android.widget.LinearLayout>
      <android.widget.FrameLayout><android.view.ViewGroup><android.view.View clickable="true"/>
      </android.view.ViewGroup></android.widget.FrameLayout>
      <android.widget.TextView/>
      <android.widget.LinearLayout>
        <android.widget.LinearLayout clickable="false"><android.widget.TextView/><android.widget.TextView/>
        </android.widget.LinearLayout>
        <android.widget.LinearLayout clickable="true"><android.widget.TextView/></android.widget.LinearLayout>
      </android.widget.LinearLayout>
    </android.widget.LinearLayout>''')
    texts = card.xpath(".//android.widget.TextView")
    for node, value in zip(texts, (title, name, timestamp, likes)):
        node.set("text", value)
    texts[-1].getparent().set("content-desc", "未点赞，喜欢" + likes + "，按钮")
    return card


class SnapshotTests(unittest.TestCase):
    def snapshot(self, cards):
        root = etree.XML("<hierarchy><android.widget.TextView text='顶部变化'/></hierarchy>")
        for card in cards:
            root.append(card)
        return ResultSnapshot(etree.tostring(root), (1080, 2400))

    def test_time_likes_ids_and_top_bar_do_not_change_signature(self):
        first = self.snapshot([native_card("标题", "作者", "1小时前", "9")])
        second_card = native_card("标题", "作者", "2小时前", "100")
        for node in second_card.iter():
            node.set("resource-id", "changed")
        second = self.snapshot([second_card])
        self.assertEqual(first.node_signature(), ("node", (("标题", "作者"),)))
        self.assertEqual(first.node_signature(), second.node_signature())

    def test_card_order_boundaries_and_duplicates_are_preserved(self):
        first = self.snapshot([native_card("甲", "作者"), native_card("甲", "作者"), native_card("乙", "作者")])
        second = self.snapshot([native_card("乙", "作者"), native_card("甲", "作者"), native_card("甲", "作者")])
        self.assertEqual(len(first.node_signature()[1]), 3)
        self.assertNotEqual(first.node_signature(), second.node_signature())
        self.assertEqual(first.candidates("作者"), [1, 2, 3])

    def test_three_unchanged_transitions_and_source_switch_reset(self):
        state = ScanState()
        node = ("node", (("标题", "作者"),))
        for expected in (False, False, False, True):
            self.assertEqual(state.update(node), expected)
        self.assertFalse(state.update(("ocr", ("标题", "作者"))))
        self.assertEqual(state.unchanged, 0)

    def test_ocr_signature_keeps_repeats_below_navigation(self):
        items = [{"text": "顶部", "box": [0, 0, 100, 50]},
                 {"text": "正文 甲", "box": [0, 200, 100, 250]},
                 {"text": "正文 甲", "box": [0, 400, 100, 450]}]
        self.assertEqual(ocr_signature(items, 100), ("ocr", ("正文甲", "正文甲")))


class AdapterTests(unittest.TestCase):
    def test_environment_check_loads_all_modules_without_running_phone_or_ocr(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("环境检查不应执行手机或OCR动作")
        names = ("find_by_xpath", "find_all_by_xpath", "get_page_source", "get_window_size",
                 "click", "swipe", "back", "sys_input", "screenshot", "open_app", "get_udid")
        phone = type("Phone", (), {name: forbidden for name in names})()
        extension = types.SimpleNamespace(process1=mock.Mock(side_effect=forbidden))
        with mock.patch("mobile_adapter._ocr_extension", return_value=extension):
            self.assertEqual(check_environment(phone)["status"], "READY")
        extension.process1.assert_not_called()

    def test_ocr_uses_actual_public_entry_and_full_results(self):
        items = [{"text": "发送", "box": [10, 20, 110, 60]}]
        extension = types.SimpleNamespace(process1=mock.Mock(return_value=types.SimpleNamespace(OCR识别结果=items)))
        phone = mock.Mock()
        adapter = MobileAdapter(phone)
        with mock.patch("mobile_adapter._ocr_extension", return_value=extension):
            self.assertEqual(adapter.ocr_screen(), items)
        phone.screenshot.assert_called_once()
        kwargs = extension.process1.call_args[1]
        self.assertTrue(kwargs["输出完整结果"])
        self.assertEqual(kwargs["文字检测框过滤的阈值"], 0.5)
        self.assertEqual(kwargs["文字检测框的大小"], 2)
        adapter.click_ocr(items, "L30")
        phone.click.assert_called_once_with(60, 40, delay_after=1)

    def test_input_is_not_appended_or_sent_by_enter(self):
        phone = mock.Mock()
        element = phone.find_by_xpath.return_value
        adapter = MobileAdapter(phone)
        adapter.input_search("关键词")
        element.input.assert_called_once_with("关键词", append=False, end_with_enter=False, delay_after=1)
        adapter.input_cursor("评论")
        phone.sys_input.assert_called_once_with("评论", False, False, delay_after=1)

    def test_ocr_accepts_actual_list_and_single_output_wrappers(self):
        items = [{"text": "发送", "score": 0.99, "box": [10, 20, 110, 60]}]
        for output in (items, [items], {"OCR识别结果": items}, [], [[]]):
            with self.subTest(output=output):
                extension = types.SimpleNamespace(process1=mock.Mock(return_value=output))
                phone = mock.Mock()
                with mock.patch("mobile_adapter._ocr_extension", return_value=extension):
                    actual = MobileAdapter(phone).ocr_screen()
                self.assertEqual(actual, items if output not in ([], [[]]) else [])

    def test_filter_list_results_click_both_options_before_scanning(self):
        from mobile_executor import Executor

        items = [{"text": "一天内", "box": [10, 100, 110, 140]},
                 {"text": "查看结果", "box": [200, 500, 400, 560]}]
        for output in (items, [items]):
            with self.subTest(wrapped=output is not items):
                phone = mock.Mock()
                adapter = MobileAdapter(phone)
                snapshot = mock.Mock()
                snapshot.candidates.return_value = [1]
                executor = Executor(adapter, mock.Mock(), sleep=lambda seconds: None)
                extension = types.SimpleNamespace(process1=mock.Mock(return_value=output))
                with mock.patch("mobile_adapter._ocr_extension", return_value=extension), \
                        mock.patch.object(executor, "switch_section"), \
                        mock.patch.object(executor, "verify_candidate", return_value="MATCH"), \
                        mock.patch.object(adapter, "snapshot", return_value=snapshot):
                    result = executor.find_work(
                        {"content_type": "视频", "expected_author": "作者"},
                        (0, 100, 1080, 200))
                self.assertEqual(result, (True, False))
                extension.process1.assert_called_once()
                self.assertEqual(phone.click.call_args_list,
                                 [mock.call(60, 120, delay_after=1),
                                  mock.call(300, 530, delay_after=1)])

    def test_profile_id_wait_is_three_seconds_and_no_nickname_fallback(self):
        phone = mock.Mock()
        phone.find_all_by_xpath.return_value = []
        phone.get_page_source.return_value = "<root><name text='作者' content-desc='复制名字和修改备注'/></root>"
        self.assertEqual(MobileAdapter(phone).profile(), ("", "作者"))
        self.assertEqual(phone.find_all_by_xpath.call_args_list,
                         [mock.call(loc.get_xpath("L16"), timeout=3)])

    def test_exists_reads_current_xml_without_zero_timeout_polling(self):
        phone = mock.Mock()
        phone.get_page_source.side_effect = ["<root/>",
            "<root><tab content-desc='已选中，推荐，按钮'><title text='推荐'/></tab></root>"]
        adapter = MobileAdapter(phone)
        self.assertFalse(adapter.exists("L02"))
        self.assertTrue(adapter.exists("L02"))
        phone.find_all_by_xpath.assert_not_called()

    def test_navigation_and_results_swipes_use_current_device_size(self):
        phone = mock.Mock()
        phone.get_window_size.return_value = (1080, 2400)
        adapter = MobileAdapter(phone)
        adapter.nav_swipe((0, 100, 1080, 200), "left")
        phone.swipe.assert_called_with(864, 150, 216, 150, swipe_time=800, delay_after=1)
        adapter.results_swipe((0, 100, 1080, 200))
        self.assertGreater(phone.swipe.call_args[0][3], 200)
        self.assertGreater(phone.swipe.call_args[0][1], phone.swipe.call_args[0][3])


if __name__ == "__main__":
    unittest.main()
