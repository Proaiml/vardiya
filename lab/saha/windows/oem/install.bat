@echo off
rem Runs once inside the Windows guest after its unattended installation (dockurr/windows OEM hook).
rem Enables WinRM for the lab network only and installs the CtmAgent service. Lab-only accounts and settings.
mkdir C:\ctm\logs 2>nul
copy /y C:\OEM\CtmAgent.cs C:\ctm\CtmAgent.cs
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /out:C:\ctm\CtmAgent.exe /r:System.ServiceProcess.dll C:\ctm\CtmAgent.cs > C:\ctm\logs\derleme.txt 2>&1
(echo server=js7-controller& echo port=7005) > C:\ctm\agent.cfg
powershell -NoProfile -Command "New-EventLog -LogName Application -Source CtmAgent -ErrorAction SilentlyContinue"
sc.exe create CtmAgent binPath= "C:\ctm\CtmAgent.exe" start= auto DisplayName= "Control-M Agent (lab)"
sc.exe failure CtmAgent reset= 0 actions= ""
sc.exe start CtmAgent
powershell -NoProfile -Command "Enable-PSRemoting -Force -SkipNetworkProfileCheck; Set-Item WSMan:\localhost\Service\AllowUnencrypted $true; Set-Item WSMan:\localhost\Service\Auth\Basic $true; Set-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -RemoteAddress Any; New-NetFirewallRule -DisplayName 'WinRM lab' -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow"
echo hazir > C:\ctm\hazir.txt
