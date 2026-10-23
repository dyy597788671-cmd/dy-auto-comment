param([string]$LanIp = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
. (Join-Path $PSScriptRoot 'Installed-Tool-Common.ps1')
$configuration = Get-InstalledToolConfig $PSScriptRoot
$python = Get-InstalledToolPython $configuration.Root
$addresses = @(Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred |
    Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.|0\.)' } |
    Select-Object -ExpandProperty IPAddress -Unique)
if ($LanIp) {
    if ($addresses -notcontains $LanIp) { throw '指定IP不属于当前运行电脑。' }
} elseif ($addresses.Count -eq 1) { $LanIp = $addresses[0] }
else { throw ('无法唯一选择局域网IPv4，请用-LanIp指定：' + ($addresses -join '、')) }
$url = 'http://127.0.0.1:' + $configuration.Port
$lanUrl = 'http://' + $LanIp + ':' + $configuration.Port
$context = Get-InstalledToolContext $url
if ($context) {
    if ($context.data.application -ne 'douyin-local-tool' -or $context.data.version -ne '1.2.0' -or $context.data.lan_url -ne $lanUrl) {
        throw '原端口正在运行其它版本或地址的后台，请关闭对应后台窗口后重开。'
    }
    Start-Process $url
    Write-Host '已打开现有网页后台；保持原后台窗口开启。'
    exit 0
}
$info = [Diagnostics.ProcessStartInfo]::new()
$info.FileName = $python
$info.Arguments = '-u "' + (Join-Path $configuration.Root 'lan_tool\server.py') + '" --root "' + $configuration.Root + '" --port ' + $configuration.Port + ' --lan-ip ' + $LanIp
$info.WorkingDirectory = $configuration.Root
$info.UseShellExecute = $false
$process = [Diagnostics.Process]::new()
$process.StartInfo = $info
$started = $false
try {
    $started = $process.Start()
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline -and -not $process.HasExited) {
        $context = Get-InstalledToolContext $url
        if ($context -and $context.data.application -eq 'douyin-local-tool' -and $context.data.version -eq '1.2.0' -and $context.data.lan_url -eq $lanUrl) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw '网页后台未通过HTTP检查，请保留上方实际错误。' }
    Write-Host ('本机HTTP检查通过；其他电脑访问：' + $lanUrl) -ForegroundColor Green
    Start-Process $url
    $process.WaitForExit()
    throw ('网页后台已停止，退出码=' + $process.ExitCode)
} finally {
    if ($started -and -not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
    $process.Dispose()
}
