# Read-only: outputs a minimal inventory; no account names, serials or private files.
[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z]:$')][string]$Drive = 'C:',
    [string]$VBoxManage = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
)
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$volume = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$Drive'"
if (-not $volume) { throw 'Selected volume does not exist' }
$version = ''
if (Test-Path -LiteralPath $VBoxManage -PathType Leaf) {
    $version = (& $VBoxManage --version | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'VirtualBox version query failed' }
}
[ordered]@{
    captured_at = [DateTime]::UtcNow.ToString('o')
    os_caption = [string]$os.Caption
    ram_available_gib = [math]::Round($os.FreePhysicalMemory / 1MB, 3)
    disk_free_gib = [math]::Round($volume.FreeSpace / 1GB, 3)
    drive_type = [int]$volume.DriveType
    virtualbox_version = $version
    hypervisor_present = [bool]$computer.HypervisorPresent
} | ConvertTo-Json
