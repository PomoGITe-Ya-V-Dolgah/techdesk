<#
  Сбор данных о компьютере для реестра techdesk (Windows 10/11, PowerShell 5+).
  Дописывает одну строку в CSV в формате импорта techdesk
  (Оборудование → Импорт из Excel). Права администратора не нужны.

  Пример (запускать на ПК сотрудника):
    powershell -ExecutionPolicy Bypass -File collect_pc.ps1 -Inventory PC-205-014 -Room "Кабинет 205" -Employee "Петрова Елена"

  Удобно положить скрипт и файл pcs.csv в общую папку и указать -Out \\SRV-01\inventory\pcs.csv
#>
param(
    [string]$Out = (Join-Path $PSScriptRoot "pcs.csv"),
    [string]$Inventory = "",
    [string]$Room = "Не указан",
    [string]$Employee = "",
    [string]$Department = ""
)

$cs   = Get-CimInstance Win32_ComputerSystem
$bios = Get-CimInstance Win32_BIOS
$os   = Get-CimInstance Win32_OperatingSystem
$net  = Get-CimInstance Win32_NetworkAdapterConfiguration -Filter "IPEnabled=True" |
        Where-Object { $_.DefaultIPGateway } | Select-Object -First 1
$ip   = $net.IPAddress | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1

$isLaptop = $cs.PCSystemType -eq 2
if (-not $Inventory) { $Inventory = "PC-$($env:COMPUTERNAME)" }

# Установленные программы (без обновлений, драйверов и библиотек)
$uninstallKeys = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)
$apps = Get-ItemProperty $uninstallKeys -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -and -not $_.SystemComponent -and -not $_.ParentKeyName } |
    Where-Object { $_.DisplayName -notmatch 'Update|Redistributable|Runtime|Driver|Драйвер|SDK' } |
    ForEach-Object { ($_.DisplayName -replace '[,;]', ' ').Trim() } |
    Sort-Object -Unique

$row = [ordered]@{
    "Инв. номер"     = $Inventory
    "Название"       = $(if ($isLaptop) { "Ноутбук $($env:COMPUTERNAME)" } else { "ПК $($env:COMPUTERNAME)" })
    "Категория"      = $(if ($isLaptop) { "Ноутбук" } else { "Рабочая станция" })
    "Кабинет"        = $Room
    "Сотрудник"      = $Employee
    "Подразделение"  = $Department
    "Статус"         = "В работе"
    "Производитель"  = $cs.Manufacturer
    "Модель"         = $cs.Model
    "Серийный номер" = $bios.SerialNumber
    "Имя ПК"         = $env:COMPUTERNAME
    "IP"             = $ip
    "MAC"            = $net.MACAddress
    "ОС"             = "$($os.Caption) $($os.Version)"
    "ПО"             = ($apps -join ", ")
    "Подключено к"   = ""
    "Примечание"     = "Собрано collect_pc.ps1 $(Get-Date -Format 'dd.MM.yyyy')"
}

[pscustomobject]$row | Export-Csv -Path $Out -Delimiter ';' -Encoding UTF8 -NoTypeInformation -Append
Write-Host "Готово: $($env:COMPUTERNAME) записан в $Out"
Write-Host "Программ найдено: $($apps.Count). Лишние можно удалить в Excel перед импортом."
