"""共享连接的抖音实例名册；只复用影刀已运行的ADB服务，不启动adb.exe。"""
import json
import os
from pathlib import Path
import re
import shlex
import socket
import struct
import tempfile
import time
from datetime import datetime, timezone

APP_PACKAGE = "com.ss.android.ugc.aweme"
REGISTRY_NAME = "mobile_instances.json"
FIELDS = ("android_user_id", "package_name", "is_primary", "display_name")


def _receive(connection, size):
    data = bytearray()
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise RuntimeError("影刀手机服务连接提前关闭")
        data.extend(part)
    return bytes(data)


def _request(connection, service):
    data = service.encode("utf-8")
    connection.sendall(("%04x" % len(data)).encode("ascii") + data)
    status = _receive(connection, 4)
    if status == b"FAIL":
        size = int(_receive(connection, 4), 16)
        raise RuntimeError(_receive(connection, size).decode("utf-8", "replace"))
    if status != b"OKAY":
        raise RuntimeError("影刀手机服务返回了未知状态")


class AdbShell:
    def __init__(self):
        # 此接口先核实5037监听程序是影刀原有adb.exe，并只查询现有设备状态。
        import lan_bridge
        self.online = lan_bridge._read_adb_online_devices()

    def __call__(self, udid, arguments, timeout=8):
        if udid.casefold() not in self.online:
            raise RuntimeError("手机不在影刀现有在线名单中：" + udid)
        command = " ".join(shlex.quote(str(value)) for value in arguments)
        with socket.create_connection(("127.0.0.1", 5037), timeout=timeout) as connection:
            connection.settimeout(timeout)
            _request(connection, "host:transport:" + udid)
            _request(connection, "shell,v2,raw:" + command)
            output, errors, total = [], [], 0
            while True:
                channel, size = struct.unpack("<BI", _receive(connection, 5))
                total += size
                if total > 16 * 1024 * 1024:
                    raise RuntimeError("手机命令输出超过16MiB")
                data = _receive(connection, size)
                if channel == 1:
                    output.append(data)
                elif channel == 2:
                    errors.append(data)
                elif channel == 3:
                    if len(data) != 1:
                        raise RuntimeError("手机命令退出状态无效")
                    stdout = b"".join(output).decode("utf-8", "replace")
                    stderr = b"".join(errors).decode("utf-8", "replace")
                    if data[0]:
                        raise RuntimeError("手机命令失败：" + (stderr or stdout).strip())
                    return stdout
                else:
                    raise RuntimeError("手机命令返回未知输出通道")


def parse_users(text):
    users = []
    for identity, name, flags in re.findall(r"UserInfo\{(\d+):(.*):([0-9a-fA-F]+)\}", text):
        users.append({"id": int(identity), "name": name, "flags": int(flags, 16)})
    if not users or len({v["id"] for v in users}) != len(users):
        raise RuntimeError("未取得有效的Android用户空间名单：" + text[:1000])
    return users


def resolve_component(text, package=APP_PACKAGE):
    matches = re.findall(r"(?m)^\s*(" + re.escape(package) + r"/[A-Za-z0-9_.$]+)\s*$", text)
    if len(set(matches)) == 1:
        return matches[0]
    if "No activity found" in text or "No activities found" in text:
        return None
    raise RuntimeError("无法确定抖音启动入口：" + text[:1000])


def foreground(text):
    # topResumedActivity优先；不能把历史任务中的任意ActivityRecord当成前台。
    for marker in ("topResumedActivity", "mResumedActivity"):
        matches = []
        for line in text.splitlines():
            if marker not in line:
                continue
            found = re.search(r"ActivityRecord\{[^\n]*?\bu(\d+)\s+([A-Za-z0-9_.]+)/", line)
            if found:
                matches.append((int(found.group(1)), found.group(2)))
        if matches:
            unique = set(matches)
            if len(unique) != 1:
                raise RuntimeError("前台存在多个活动实例，无法确认当前抖音")
            return matches[0]
    return None


def _registry_path(root):
    return Path(root) / "data" / REGISTRY_NAME


def read_registry(root):
    path = _registry_path(root)
    if not path.exists():
        return {"schema_version": 1, "phones": {}}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if value.get("schema_version") != 1 or not isinstance(value.get("phones"), dict):
        raise RuntimeError("抖音实例名册格式不正确")
    return value


def _save_registry(root, value):
    path = _registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2)
    descriptor, temporary = tempfile.mkstemp(prefix="mobile_instances_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def discover_roster(connection_infos, root, shell=None):
    if not isinstance(connection_infos, list):
        raise ValueError("connection_infos需要当前实际连接的手机详情列表")
    previous = read_registry(root)
    phones, roster = {}, []
    if shell is None and connection_infos:
        shell = AdbShell()
    for index, info in enumerate(connection_infos):
        udid = info["udid"]
        if not isinstance(udid, str) or not udid.strip() or udid in phones:
            raise ValueError("手机UDID为空或重复")
        name = info.get("custom_name") or udid
        old = previous["phones"].get(udid, {})
        phone = {"legacy_user_id": old.get("legacy_user_id"), "instances": [], "error": ""}
        phones[udid] = phone
        try:
            users = parse_users(shell(udid, ["pm", "list", "users"]))
            primary = [v["id"] for v in users if v["flags"] & 1]
            if phone["legacy_user_id"] is None:
                if len(primary) == 1:
                    phone["legacy_user_id"] = primary[0]
                else:
                    current = shell(udid, ["am", "get-current-user"]).strip()
                    if not current.isdigit() or int(current) not in {v["id"] for v in users}:
                        raise RuntimeError("无法确定当前主用户空间")
                    phone["legacy_user_id"] = int(current)
            # 旧主程序的执行账号保持原值，现有失败任务和成功动作不转交副本。
            for user in sorted(users, key=lambda v: (v["id"] != phone["legacy_user_id"], v["id"])):
                identity = user["id"]
                listing = shell(udid, ["pm", "list", "packages", "-e", "--user", identity, APP_PACKAGE])
                if "package:" + APP_PACKAGE not in {line.strip() for line in listing.splitlines()}:
                    continue
                component = resolve_component(shell(udid, ["cmd", "package", "resolve-activity", "--brief",
                    "--user", identity, "-a", "android.intent.action.MAIN", "-c",
                    "android.intent.category.LAUNCHER", APP_PACKAGE]))
                if component is None:
                    continue
                is_primary = identity == phone["legacy_user_id"]
                account = "设备_" + udid
                if not is_primary:
                    account += "_u" + str(identity) + "_" + APP_PACKAGE
                clone_number = sum(not v["is_primary"] for v in phone["instances"]) + 1
                label = " · 主抖音" if is_primary else " · 副抖音" + (str(clone_number) if clone_number > 1 else "")
                binding = {"device_id": udid, "sender_account_id": account,
                    "android_user_id": identity, "package_name": APP_PACKAGE,
                    "is_primary": is_primary, "display_name": name + label,
                    "launch_component": component, "connection_index": index}
                phone["instances"].append(binding)
            roster.extend(phone["instances"])
        except Exception as error:
            # 不用上次名单替代这次读取失败的名单，避免虚报可执行副本。
            phone["instances"] = []
            phone["error"] = str(error)
            print("手机" + name + "的抖音实例读取失败：" + str(error))
    _save_registry(root, {"schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(), "phones": phones})
    return roster


def cached_inventory(root, online):
    """网页只读取影刀发布的实例名单，与现有在线状态取交集；不发送手机命令。"""
    registry = read_registry(root)
    online = {v.casefold() for v in online}
    bindings, errors = [], []
    for udid, phone in registry["phones"].items():
        if udid.casefold() not in online:
            continue
        bindings.extend(phone["instances"])
        if phone.get("error"):
            errors.append(udid + "：" + phone["error"])
    return {"instance_count": len(bindings), "instances": bindings,
            "discovery_errors": errors, "inventory_ready": _registry_path(root).exists()}


def launch_instance(phone_device, identity, shell=None, sleep=time.sleep, monotonic=time.monotonic):
    udid = identity["device_id"]
    if phone_device.get_udid() != udid:
        raise RuntimeError("当前手机连接与任务绑定的物理手机不一致")
    user = identity.get("android_user_id")
    package = identity.get("package_name")
    if isinstance(user, bool) or not isinstance(user, int) or user < 0 or package != APP_PACKAGE:
        raise RuntimeError("抖音实例缺少有效用户空间或包名")
    shell = shell or AdbShell()
    component = resolve_component(shell(udid, ["cmd", "package", "resolve-activity", "--brief",
        "--user", user, "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", package]))
    if component is None:
        raise RuntimeError("原任务绑定的抖音实例已不可用")
    output = shell(udid, ["am", "start", "--user", user, "-n", component])
    if re.search(r"(?im)^\s*(?:Error(?:\s+type\s+\d+)?[:\s]|Exception|SecurityException)", output):
        raise RuntimeError("指定抖音实例启动失败：" + output.strip())
    deadline = monotonic() + 8
    actual = None
    while monotonic() < deadline:
        actual = foreground(shell(udid, ["dumpsys", "activity", "activities"]))
        if actual == (user, package):
            return {"status": "INSTANCE_READY", "android_user_id": user, "package_name": package}
        sleep(0.25)
    raise RuntimeError("抖音前台实例核对失败：预期用户空间" + str(user) + "，实际" + str(actual))
