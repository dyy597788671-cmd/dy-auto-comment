$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
. (Join-Path $PSScriptRoot 'Installed-Tool-Common.ps1')
$configuration = Get-InstalledToolConfig $PSScriptRoot
if (Get-Process -Name 'ShadowBot.Shell' -ErrorAction SilentlyContinue) {
    throw '请保存当前应用并完全退出影刀，再双击Apply-Instances.cmd。'
}
$context = Get-InstalledToolContext ('http://127.0.0.1:' + $configuration.Port)
if ($context -and $context.data.application -eq 'douyin-local-tool') {
    throw '请关闭原网页后台窗口，再双击Apply-Instances.cmd。'
}
$python = Get-InstalledToolPython $configuration.Root
& $python (Join-Path $PSScriptRoot 'install_instances.py') --root $configuration.Root --package $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw '实例接入更新未完成，请保留上方报错。' }
$signing = Join-Path $configuration.Root 'lan_tool\repair_signature.ps1'
& $signing -ProjectRoot (Join-Path $configuration.Root 'xbot_robot') -RuntimePath $configuration.Runtime -Write
if ($LASTEXITCODE -ne 0) { throw '应用签名处理未完成，请保留上方报错。' }
Write-Host '实例接入代码已安装。重新打开影刀，从主流程第1行运行，再刷新网页查看抖音数量。' -ForegroundColor Green
& (Join-Path $PSScriptRoot 'Start-Installed-Tool.ps1')
