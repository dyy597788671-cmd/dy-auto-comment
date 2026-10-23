"""按已确认流程执行当前抖音实例；主副共用连接，进度按实例保存。"""
import importlib
import random
import time

if __package__:
    from . import mobile_locators as loc
    from .mobile_adapter import MobileAdapter, ScanState, ocr_signature
else:
    import mobile_locators as loc
    from mobile_adapter import MobileAdapter, ScanState, ocr_signature


class Executor:
    def __init__(self, adapter, business, sleep=time.sleep, uniform=random.uniform):
        self.adapter = adapter
        self.business = business
        self.sleep = sleep
        self.uniform = uniform
        self.executed_actions = []

    def wait(self, minimum=3, maximum=8):
        self.sleep(self.uniform(minimum, maximum))

    def switch_section(self, section, nav_bounds):
        if self.adapter.exists("L07", section=section):
            self.adapter.click("L07", section=section)
            return
        directions = ("right", "left") if section == "综合" else ("left", "right")
        for direction in directions:
            for _ in range(6):
                self.adapter.nav_swipe(nav_bounds, direction)
                if self.adapter.exists("L07", section=section):
                    self.adapter.click("L07", section=section)
                    return
        raise RuntimeError("未找到搜索栏目：" + section)

    def verify_candidate(self, task, occurrence):
        self.adapter.click_xpath(loc.build_author_cover_xpath(task["expected_author"], occurrence))
        avatar = "L14" if task["content_type"] == "图文" else "L15"
        self.adapter.click(avatar, nickname=task["expected_author"])
        douyin_id, author = self.adapter.profile()
        verdict = self.business.verify_author(task, douyin_id, author)
        self.adapter.back()
        if verdict == "MISMATCH":
            self.adapter.back()
        elif verdict != "MATCH":
            raise RuntimeError("作者抖音号核验不确定，请检查任务表中的抖音号及主页读取结果")
        return verdict

    def find_work(self, task, nav_bounds):
        saw_id_mismatch = False
        for section in (task["content_type"], "综合"):
            self.switch_section(section, nav_bounds)
            self.wait(5, 6)
            self.adapter.click("L08")
            filter_items = self.adapter.ocr_screen()
            self.adapter.click_ocr(filter_items, "L09")
            self.adapter.click_ocr(filter_items, "L10")
            scan = ScanState()
            snapshot = self.adapter.snapshot()
            while True:
                occurrences = snapshot.candidates(task["expected_author"])
                for occurrence in occurrences:
                    # 返回列表后使用新快照核对当前候选，不沿用旧元素对象。
                    if occurrence not in snapshot.candidates(task["expected_author"]):
                        continue
                    verdict = self.verify_candidate(task, occurrence)
                    if verdict == "MATCH":
                        return True, saw_id_mismatch
                    saw_id_mismatch = True
                    snapshot = self.adapter.snapshot()
                signature = snapshot.node_signature()
                if signature is None:
                    signature = ocr_signature(self.adapter.ocr_screen(),
                                              (nav_bounds[1] + nav_bounds[3]) // 2)
                if scan.update(signature):
                    break
                self.adapter.results_swipe(nav_bounds)
                snapshot = self.adapter.snapshot()
        return False, saw_id_mismatch

    def record(self, task, action):
        self.executed_actions = self.business.record_action_result(
            self.executed_actions, action, "PASSED", "", task_data=task)

    def video_comment(self, task):
        self.wait()
        self.adapter.click("L21")
        self.wait()
        self.adapter.click("L22")
        self.wait()
        self.adapter.input_cursor(task["comment_content"])
        self.wait()
        self.adapter.click("L23")
        self.record(task, "Comment")
        self.adapter.back()

    def photo_comment(self, task):
        self.wait()
        self.adapter.click("L24")
        for _ in range(2):
            self.wait()
            if not self.adapter.exists("L24"):
                break
            self.wait()
            self.adapter.click("L24")
        self.wait()
        if self.adapter.exists("L24"):
            raise RuntimeError("图文评论按钮已点击3次，仍未打开评论输入框。")
        self.wait()
        self.adapter.input_cursor(task["comment_content"])
        self.wait()
        self.adapter.click("L23")
        self.record(task, "Comment")

    def interact(self, task):
        plan = self.business.prepare_interactions(task)
        for action in plan["execution_order"]:
            if action in ("Like", "Favorite"):
                self.wait()
                self.adapter.click("L19" if action == "Like" else "L25")
                self.record(task, action)
            elif action == "Comment":
                if task["content_type"] == "视频":
                    self.video_comment(task)
                else:
                    self.photo_comment(task)
            elif action == "Share":
                self.wait()
                self.adapter.click("L27")
                self.wait()
                self.adapter.click("L29")
                self.wait()
                self.adapter.click_ocr(self.adapter.ocr_screen(), "L30")
                self.record(task, "Share")
                self.wait(5, 10)
            else:
                raise RuntimeError("未知互动动作：" + str(action))

    def execute(self, task):
        self.executed_actions = list(task.get("action_results", []))
        self.adapter.open_app()
        self.wait(3, 10)
        # 只在启动后的初始化阶段无限回退；末尾不重复。
        while not self.adapter.exists("L02"):
            self.adapter.back()
            self.sleep(2)
        self.adapter.click("L03")
        self.adapter.input_search(task["keyword"])
        self.adapter.click("L05")
        nav_bounds = self.adapter.bounds("L06")
        found, saw_id_mismatch = self.find_work(task, nav_bounds)
        if not found:
            return self.business.finish_task(
                task, [], status="NOT_FOUND",
                log_message="抖音号不同" if saw_id_mismatch else "未找到目标作品")
        self.interact(task)
        return self.business.finish_task(task, self.executed_actions, status="SUCCESS",
                                         log_message="互动指令执行完成")


def run(phone_device, device_identity):
    """子流程入口：复用现有连接、任务绑定、即时进度及异常结束接口。"""
    business = importlib.import_module(".module1", __package__) if __package__ else importlib.import_module("module1")
    account = device_identity["sender_account_id"]
    physical = device_identity["device_id"]
    task_id = device_identity.get("task_id")
    try:
        if "android_user_id" not in device_identity:
            raise RuntimeError("主流程尚未读取抖音实例名单，请从主流程第1行运行")
        task = business.read_task(sender_account_id=account, physical_device_id=physical,
                                  resume_active=False, wait_for_task=False)
        if task is None:
            return {"status": "NO_TASK"}
        if task_id is not None and str(task["task_id"]) != str(task_id):
            raise RuntimeError("当前任务与主流程绑定Task_ID不一致")
        for name in ("android_user_id", "package_name"):
            if name in task and task[name] != device_identity[name]:
                raise RuntimeError("当前抖音实例与原任务绑定不一致")
        return Executor(MobileAdapter(phone_device, device_identity), business).execute(task)
    except Exception as error:
        print("设备异常：" + str(error))
        outcome = business.finish_device_error(account, physical, str(error), task_id)
        if not outcome.get("released"):
            raise
        return {"status": "FAILED", "error": str(error), "task_id": task_id}
