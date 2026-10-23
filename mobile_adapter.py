"""手机与离线OCR适配。接口依据B的两份真实报告，支持Python 3.7。"""
import importlib
import re
import sys
import tempfile
from pathlib import Path

from lxml import etree

if __package__:
    from . import mobile_locators as loc
else:
    import mobile_locators as loc


def parse_bounds(value):
    match = re.fullmatch(r"\s*\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]\s*", value or "")
    if not match:
        raise ValueError("手机节点bounds格式无效：" + str(value))
    return tuple(int(item) for item in match.groups())


def _compact(value):
    return "".join((value or "").split())


def _xml_root(source):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.fromstring(source.encode("utf-8") if isinstance(source, str) else source,
                            parser=parser)


def _visible(node, size):
    if node.get("displayed") == "false":
        return False
    if not node.get("bounds"):
        return True
    left, top, right, bottom = parse_bounds(node.get("bounds"))
    return right > max(left, 0) and bottom > max(top, 0) and left < size[0] and top < size[1]


class ResultSnapshot:
    """同一份结果页XML供候选遍历和内容签名共用。"""
    def __init__(self, source, size):
        self.root = _xml_root(source)
        self.size = size
        self.authors = self.root.xpath(loc.XPATHS["L11"] + " | " + loc.XPATHS["L12"])

    def candidates(self, nickname):
        occurrence = 0
        result = []
        for node in self.authors:
            if node.get("text", "") == nickname:
                occurrence += 1
                if _visible(node, self.size):
                    result.append(occurrence)
        return result

    def node_signature(self):
        cards = []
        seen_cards = set()
        native = set(self.root.xpath(loc.XPATHS["L11"]))
        for author in self.authors:
            if not _visible(author, self.size):
                continue
            relative = (loc.NATIVE_RELATIVE_CARD_XPATH if author in native
                        else loc.COMPOSE_RELATIVE_CARD_XPATH)
            selected = author.xpath(relative)
            if not selected:
                continue
            card = selected[0]
            if card in seen_cards:
                continue
            seen_cards.add(card)
            texts = []
            # 传统/Compose卡片中的标题在作者前，时间、赞数在作者后。
            # 保留标题与作者节点；不把操作描述、时间、数字统计并入签名。
            for node in card.iter():
                if node is author:
                    text = _compact(node.get("text"))
                    if text:
                        texts.append(text)
                    break
                if node.tag != "android.widget.TextView" or not _visible(node, self.size):
                    continue
                text = _compact(node.get("text"))
                if not text:
                    continue
                action_ancestor = any(
                    re.search(r"喜欢|收藏|分享|评论|^赞\s*\d", parent.get("content-desc", ""))
                    for parent in node.iterancestors() if parent is not card
                )
                if not action_ancestor:
                    texts.append(text)
            if texts:
                cards.append(tuple(texts))
        return ("node", tuple(cards)) if cards else None


def ocr_signature(items, nav_middle_y):
    texts = []
    for item in items:
        box = item["box"]
        if (box[1] + box[3]) / 2 > nav_middle_y:
            text = _compact(item["text"])
            if text:
                texts.append(text)
    return ("ocr", tuple(sorted(texts)))


class ScanState:
    def __init__(self):
        self.previous = None
        self.unchanged = 0

    def update(self, signature):
        self.unchanged = self.unchanged + 1 if signature == self.previous else 0
        self.previous = signature
        return self.unchanged >= 3


def _ocr_extension():
    # 调用已安装扩展的公开入口；保留其自己的初始化与资源/依赖处理。
    return importlib.import_module("xbot_extensions.activity_179ea575")


def check_environment(phone_device):
    """安装后检查模块与入口能否加载；不执行手机动作或OCR识别。"""
    methods = ("find_by_xpath", "find_all_by_xpath", "get_page_source", "get_window_size",
               "click", "swipe", "back", "sys_input", "screenshot", "open_app", "get_udid")
    missing = [name for name in methods if not callable(getattr(type(phone_device), name, None))]
    if missing:
        raise RuntimeError("手机对象缺少接口：" + ", ".join(missing))
    extension = _ocr_extension()
    if not callable(getattr(extension, "process1", None)):
        raise RuntimeError("当前离线OCR公开入口process1不可用")
    executor = (importlib.import_module(".mobile_executor", __package__) if __package__
                else importlib.import_module("mobile_executor"))
    if not callable(getattr(executor, "run", None)):
        raise RuntimeError("mobile_executor.run入口不可用")
    result = {"status": "READY", "python_version": sys.version.split()[0],
              "ocr_entry": "xbot_extensions.activity_179ea575.process1"}
    print("手机执行模块环境检查通过：Python " + result["python_version"] + "，离线OCR入口可用。")
    return result


class MobileAdapter:
    def __init__(self, phone_device, device_identity=None):
        self.device = phone_device
        self.device_identity = device_identity

    def exists(self, locator_id, **parameters):
        # 从当前XML判断存在性，不假定旧SDK的timeout=0轮询行为。
        root = _xml_root(self.device.get_page_source())
        return bool(root.xpath(loc.get_xpath(locator_id, **parameters)))

    def click(self, locator_id, **parameters):
        self.click_xpath(loc.get_xpath(locator_id, **parameters))

    def click_xpath(self, expression):
        element = self.device.find_by_xpath(expression, timeout=5)
        element.click(delay_after=1, anchor_type="center")

    def input_search(self, text):
        element = self.device.find_by_xpath(loc.get_xpath("L04"), timeout=5)
        element.input(text, append=False, end_with_enter=False, delay_after=1)

    def input_cursor(self, text):
        self.device.sys_input(text, False, False, delay_after=1)

    def bounds(self, locator_id):
        element = self.device.find_by_xpath(loc.get_xpath(locator_id), timeout=5)
        return parse_bounds(element.get_attribute("bounds"))

    def profile(self):
        # 查找抖音号最多等待3秒；不以昵称或认证文字代替。
        ids = self.device.find_all_by_xpath(loc.get_xpath("L16"), timeout=3)
        names = _xml_root(self.device.get_page_source()).xpath(loc.get_xpath("L17"))
        if len(ids) > 1 or len(names) > 1:
            raise RuntimeError("作者主页信息定位到多个节点")
        return (ids[0].get_text() if ids else "", names[0].get("text", "") if names else "")

    def snapshot(self):
        return ResultSnapshot(self.device.get_page_source(), self.device.get_window_size())

    def open_app(self):
        if self.device_identity is None:
            self.device.open_app(loc.APP_PACKAGE)
        else:
            import mobile_instances
            mobile_instances.launch_instance(self.device, self.device_identity)

    def back(self):
        self.device.back(delay_after=1)

    def nav_swipe(self, bounds, direction):
        left, top, right, bottom = bounds
        y = (top + bottom) // 2
        x20 = left + (right - left) * 20 // 100
        x80 = left + (right - left) * 80 // 100
        start, end = (x80, x20) if direction == "left" else (x20, x80)
        self.device.swipe(start, y, end, y, swipe_time=800, delay_after=1)

    def results_swipe(self, nav_bounds):
        width, height = self.device.get_window_size()
        top = nav_bounds[3]
        available = height - top
        self.device.swipe(width // 2, top + available * 80 // 100,
                          width // 2, top + available * 20 // 100,
                          swipe_time=800, delay_after=1)

    def ocr_screen(self):
        directory = Path(tempfile.gettempdir())
        filename = "dy_mobile_executor_screen.png"
        self.device.screenshot(str(directory), filename=filename)
        output = _ocr_extension().process1(
            图片路径或图片url=str(directory / filename), 输出完整结果=True,
            文字检测框过滤的阈值=0.5, 文字检测框的大小=2)
        items = output["OCR识别结果"] if isinstance(output, dict) else output.OCR识别结果
        if not isinstance(items, list):
            raise TypeError("离线OCR未返回完整结果列表")
        return items

    def click_ocr(self, items, locator_id):
        text = loc.OCR_TEXT[locator_id]
        for item in items:
            if item["text"].strip() == text:
                left, top, right, bottom = item["box"]
                self.device.click((left + right) // 2, (top + bottom) // 2, delay_after=1)
                return
        raise RuntimeError("离线OCR未找到文字：" + text)
