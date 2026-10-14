"""Read ShadowBot's registration and the existing ADB server's device list."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DISCOVER = r"""+$ErrorActionPreference = 'Stop'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $OutputEncoding
$adbProcesses = @(Get-CimInstance Win32_Process -Filter "Name='adb.exe'" |
    Select-Object ProcessId, ExecutablePath, CommandLine)
$adbIds = @($adbProcesses | ForEach-Object { $_.ProcessId })
$listeners = @()
if ($adbIds.Count -gt 0) {
    $listeners = @(Get-NetTCPConnection -State Listen |
        Where-Object { $adbIds -contains $_.OwningProcess } |
        Select-Object LocalAddress, LocalPort, OwningProcess)
}
[pscustomobject]@{ processes=$adbProcesses; listeners=$listeners } |
    ConvertTo-Json -Depth 5 -Compress
"""


def device_rows(output):
    rows = []
    for line in output.splitlines():
        match = re.match(r"^([^\s]+)\s+(device|offline|unauthorized|recovery|sideload|bootloader)\b(.*)$", line.strip())
        if match:
            rows.append({"serial": match[1], "state": match[2], "details": match[3].strip()})
    return rows


def run(command, timeout=15):
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or "查询命令失败")
    return result.stdout


def collect():
    config = Path(os.environ["LOCALAPPDATA"]) / "ShadowBot" / "mobile_device_connects.json"
    report = {"collected_at": datetime.now().astimezone().isoformat(), "connection_file": str(config)}
    registered = json.loads(config.read_text(encoding="utf-8-sig"))
    if not isinstance(registered, list):
        raise ValueError("影刀连接文件结构与已提供文件不同")
    report["shadowbot_devices"] = [{key: row.get(key) for key in
        ("Udid", "CustomName", "PlatformName", "IsConnected", "IsReady")} for row in registered]
    environment = json.loads(run(["powershell.exe", "-NoProfile", "-Command", DISCOVER]))
    report["adb_processes"] = environment.get("processes") or []
    report["adb_listeners"] = environment.get("listeners") or []
    queries = []
    seen = set()
    for proc in report["adb_processes"]:
        executable = proc.get("ExecutablePath")
        if not executable or not Path(executable).is_file():
            continue
        smart_ports = {5037}
        command_line = proc.get("CommandLine") or ""
        socket_port = re.search(r'''(?:^|\s)-L\s+["']?tcp:[^\s"']*:(\d+)''', command_line)
        if socket_port:
            smart_ports = {int(socket_port[1])}
        for listener in report["adb_listeners"]:
            if listener["OwningProcess"] != proc["ProcessId"]:
                continue
            if int(listener["LocalPort"]) not in smart_ports:
                continue
            address = listener["LocalAddress"]
            if address in ("0.0.0.0", "127.0.0.1"):
                server_host = "127.0.0.1"
            elif address in ("::", "::1"):
                server_host = "::1"
            else:
                server_host = address
            port = int(listener["LocalPort"])
            endpoint = (proc["ProcessId"], port)
            if endpoint in seen:
                continue
            seen.add(endpoint)
            item = {"path": executable, "server_host": server_host, "server_port": port}
            try:
                # Match the running server's executable and endpoint. No start/kill/reconnect commands.
                output = run([executable, "-H", server_host, "-P", str(port), "devices", "-l"], timeout=10)
                if "List of devices attached" not in output:
                    raise RuntimeError("现有监听端口没有返回ADB设备列表")
                item.update(raw_output=output.strip(), devices=device_rows(output))
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                item["error"] = str(exc)
            queries.append(item)
    report["adb_queries"] = queries
    valid = [query for query in queries if "devices" in query]
    if len(valid) == 1:
        known = {str(row.get("Udid")) for row in registered if row.get("PlatformName") == "Android" and row.get("Udid")}
        online = {row["serial"] for row in valid[0]["devices"] if row["state"] == "device"}
        report["online_registered_serials"] = sorted(known & online)
        report["online_registered_count"] = len(known & online)
        report["online_unregistered_serials"] = sorted(online - known)
    else:
        report["online_registered_count"] = None
        report["count_note"] = "未取得唯一ADB服务的设备列表；保留现场输出供确认，不猜测总数。"
    return report


def main():
    target = Path(__file__).resolve().parent / "Device-Connection-Report.txt"
    try:
        report = collect()
    except Exception as exc:
        report = {"collected_at": datetime.now().astimezone().isoformat(), "collection_error": str(exc)}
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")
    print("REPORT=" + str(target))
    count = report.get("online_registered_count")
    print("ONLINE_REGISTERED_COUNT=" + (str(count) if count is not None else "UNCONFIRMED"))
    print("UPLOAD: Device-Connection-Report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
