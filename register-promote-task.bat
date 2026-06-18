@echo off
setlocal
chcp 65001 >nul
schtasks /Create /TN "PromoteJarvisJunction" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"D:\\Venu\\jarvis\\promote-junction.ps1\"" /SC ONLOGON /RL HIGHEST /F
echo ---
schtasks /Query /TN "PromoteJarvisJunction" /FO LIST
endlocal
