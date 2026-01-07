$DesktopPath = [Environment]::GetFolderPath('Desktop')
$RootDir = Split-Path -Parent $PSScriptRoot
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Gang Sheet Generator.lnk")
$Shortcut.TargetPath = "$RootDir\dist\GangSheetGenerator.exe"
$Shortcut.WorkingDirectory = "$RootDir\dist"
$Shortcut.Save()
Write-Host "Desktop shortcut created!" -ForegroundColor Green
