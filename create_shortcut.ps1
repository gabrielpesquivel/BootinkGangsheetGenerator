$DesktopPath = [Environment]::GetFolderPath('Desktop')
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Gang Sheet Generator.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\dist\GangSheetGenerator.exe"
$Shortcut.WorkingDirectory = "$PSScriptRoot\dist"
$Shortcut.Save()
Write-Host "Desktop shortcut created!" -ForegroundColor Green
