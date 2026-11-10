# Run inside the dedicated Server guest, never on the host.
[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][guid]$ExpectedVmUuid)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$computer = Get-CimInstance Win32_ComputerSystem
$product = Get-CimInstance Win32_ComputerSystemProduct
$os = Get-CimInstance Win32_OperatingSystem
if ($computer.Model -ne 'VirtualBox' -or $os.ProductType -ne 3 -or
    [guid]$product.UUID -ne $ExpectedVmUuid -or $computer.PartOfDomain) {
    throw 'Expected the explicitly selected, standalone VirtualBox Server guest.'
}
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run as guest Administrator.'
}
$adapters = @(Get-NetAdapter -Physical)
if ($adapters.Count -ne 1 -or $adapters[0].Status -ne 'Up') { throw 'Expected one connected lab adapter.' }
$index = $adapters[0].ifIndex
if (@(Get-NetRoute -InterfaceIndex $index -ErrorAction SilentlyContinue | Where-Object DestinationPrefix -in @('0.0.0.0/0','::/0')).Count) {
    throw 'Remove default routes and verify internal-only networking before configuring the lab.'
}
$addresses = @(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4)
if (@($addresses | Where-Object { $_.IPAddress -ne '10.77.0.10' -and $_.IPAddress -notlike '169.254.*' }).Count) {
    throw 'Unexpected address on the guest; refusing to overwrite it.'
}
if (@($addresses | Where-Object { $_.IPAddress -eq '10.77.0.10' -and $_.PrefixLength -ne 24 }).Count) {
    throw 'Existing lab address has the wrong subnet prefix.'
}
if (-not $PSCmdlet.ShouldProcess($computer.Name, 'Set lab IP/DNS/name and install AD DS, DNS and management tools')) {
    return
}
$logDirectory = 'C:\ProgramData\NorthstarLab\Logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$auditPath = Join-Path $logDirectory 'server-bootstrap.jsonl'
function Write-LabAudit([string]$Stage, [string]$Outcome) {
    [ordered]@{ time = [DateTime]::UtcNow.ToString('o'); stage = $Stage; outcome = $Outcome } |
        ConvertTo-Json -Compress | Add-Content -LiteralPath $auditPath
}
try {
    Write-LabAudit 'bootstrap' 'started'
    if (-not @($addresses | Where-Object IPAddress -eq '10.77.0.10').Count) {
        New-NetIPAddress -InterfaceIndex $index -IPAddress '10.77.0.10' -PrefixLength 24 | Out-Null
    }
    Set-DnsClientServerAddress -InterfaceIndex $index -ServerAddresses '10.77.0.10'
    Write-LabAudit 'network' 'configured'
    $result = Install-WindowsFeature AD-Domain-Services,DNS,GPMC -IncludeManagementTools
    if (-not $result.Success) { throw 'Role installation did not succeed; inspect Windows feature logs.' }
    Write-LabAudit 'roles' 'installed'
    if ($computer.Name -ne 'RH-LAB-DC01') { Rename-Computer -NewName 'RH-LAB-DC01' -Force }
    Write-LabAudit 'bootstrap' 'completed-restart-required'
    [ordered]@{ ComputerNameAfterRestart = 'RH-LAB-DC01'; Address = '10.77.0.10/24'; RestartRequired = $true; DomainCreated = $false } | ConvertTo-Json
} catch {
    Write-LabAudit 'bootstrap' 'failed-partial-changes-possible'
    throw
}
