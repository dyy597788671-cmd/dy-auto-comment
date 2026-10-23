function Get-InstalledToolConfig([string]$Directory) {
    $path = Join-Path $Directory 'setup_tool.ps1'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw '请将更新包全部文件解压到原工具启动目录，与原setup_tool.ps1放在一起。'
    }
    # Read constant defaults only. Never execute the old installer.
    $tokens = $null
    $parseErrors = $null
    $tree = [Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count) { throw '原工具配置文件解析失败，尚未运行安装。' }
    $defaults = @{}
    foreach ($parameter in $tree.ParamBlock.Parameters) {
        $name = $parameter.Name.VariablePath.UserPath
        if ($name -in @('ProjectRoot', 'RuntimePath', 'Port')) {
            $defaults[$name] = $parameter.DefaultValue.SafeGetValue()
        }
    }
    if (-not $defaults.ProjectRoot -or -not $defaults.RuntimePath) {
        throw '原工具未提供应用目录或Runtime路径。'
    }
    $root = (Resolve-Path -LiteralPath $defaults.ProjectRoot).ProviderPath
    if (-not (Test-Path -LiteralPath (Join-Path $root 'data\task_cases.xlsx') -PathType Leaf)) {
        throw ('原工具指定的应用目录缺少任务表：' + $root)
    }
    if (-not $defaults.Port) { $defaults.Port = 8765 }
    return [pscustomobject]@{ Root=$root; Runtime=[string]$defaults.RuntimePath; Port=[int]$defaults.Port }
}

function Get-InstalledToolPython([string]$Root) {
    $python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw '未找到此前已验证的Python313解释器。'
    }
    & $python -c "import sys,sqlite3; assert sys.version_info >= (3,8); sqlite3.connect(':memory:')"
    if ($LASTEXITCODE -ne 0) { throw 'Python检查未通过。' }
    return $python
}

function Get-InstalledToolContext([string]$Address) {
    $request = [Net.WebRequest]::Create($Address + '/api/context')
    $request.Proxy = $null
    $request.Timeout = 2000
    $request.ReadWriteTimeout = 2000
    $response = $null
    $reader = $null
    try {
        $response = $request.GetResponse()
        $reader = [IO.StreamReader]::new($response.GetResponseStream())
        return ($reader.ReadToEnd() | ConvertFrom-Json)
    } catch { return $null }
    finally {
        if ($reader) { $reader.Dispose() }
        if ($response) { $response.Dispose() }
    }
}
