$DesktopPath = [Environment]::GetFolderPath('Desktop')
$RootDir = Split-Path -Parent $PSScriptRoot
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Gang Sheet Generator.lnk")
# Run from source so changes are always reflected
$Shortcut.TargetPath = "pythonw"
$Shortcut.Arguments = "`"$PSScriptRoot\gui.py`""
$Shortcut.WorkingDirectory = "$RootDir"
$Shortcut.Save()
Write-Host "Desktop shortcut created (runs from source)!" -ForegroundColor Green
