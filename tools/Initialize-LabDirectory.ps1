[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][guid]$ExpectedVmUuid)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$computer=Get-CimInstance Win32_ComputerSystem
$product=Get-CimInstance Win32_ComputerSystemProduct
if ($computer.Model -ne 'VirtualBox' -or [guid]$product.UUID -ne $ExpectedVmUuid -or
    $computer.Name -ne 'RH-LAB-DC01' -or $computer.Domain -ne 'ad.northstar.test') {
    throw 'Expected the selected Northstar lab domain controller.'
}
Import-Module ActiveDirectory
$domain=Get-ADDomain
if ($domain.DNSRoot -ne 'ad.northstar.test' -or $domain.NetBIOSName -ne 'NORTHSTAR') { throw 'Unexpected domain.' }
$base=$domain.DistinguishedName
$root="OU=NorthstarLab,$base"
$marker='Managed by windows-identity-lab; fictional lab objects only'
$ous=@(
    @{Name='NorthstarLab'; Path=$base},
    @{Name='People'; Path=$root},
    @{Name='Groups'; Path=$root},
    @{Name='Workstations'; Path=$root},
    @{Name='DisabledPeople'; Path=$root}
)
$groups=@(
    @{Name='GG_HR_Staff'; Scope='Global'},
    @{Name='GG_IT_Staff'; Scope='Global'},
    @{Name='GG_Auditors'; Scope='Global'},
    @{Name='DL_HR_Read'; Scope='DomainLocal'},
    @{Name='DL_HR_Modify'; Scope='DomainLocal'},
    @{Name='DL_IT_Read'; Scope='DomainLocal'},
    @{Name='DL_IT_Modify'; Scope='DomainLocal'}
)
$links=@(
    @{Member='GG_HR_Staff'; Target='DL_HR_Modify'},
    @{Member='GG_IT_Staff'; Target='DL_IT_Modify'},
    @{Member='GG_Auditors'; Target='DL_HR_Read'},
    @{Member='GG_Auditors'; Target='DL_IT_Read'}
)
# Check all name collisions before making any changes. Never adopt unrelated objects.
foreach($ou in $ous) {
    $dn="OU=$($ou.Name),$($ou.Path)"
    $existing=Get-ADObject -LDAPFilter "(distinguishedName=$dn)" -Properties Description
    if($existing -and ($existing.ObjectClass -ne 'organizationalUnit' -or $existing.Description -ne $marker)) {
        throw "Unmanaged OU collision: $dn"
    }
}
foreach($group in $groups) {
    $name=$group.Name
    $existing=Get-ADObject -LDAPFilter "(|(sAMAccountName=$name)(distinguishedName=CN=$name,OU=Groups,$root))" -Properties Description
    foreach($object in @($existing)) {
        if($object.ObjectClass -ne 'group' -or $object.DistinguishedName -ne "CN=$name,OU=Groups,$root" -or $object.Description -ne $marker) {
            throw "Unmanaged group collision: $name"
        }
        $actual=Get-ADGroup -Identity $object.DistinguishedName
        if($actual.GroupScope.ToString() -ne $group.Scope -or $actual.GroupCategory.ToString() -ne 'Security') {
            throw "Unexpected group scope/category: $name"
        }
    }
}
if(-not $PSCmdlet.ShouldProcess($root,'Create five protected OUs, seven empty security groups and four group nesting links')) { return }
$createdOus=0; $createdGroups=0; $addedLinks=0
foreach($ou in $ous) {
    $dn="OU=$($ou.Name),$($ou.Path)"
    if(-not (Get-ADObject -LDAPFilter "(distinguishedName=$dn)")) {
        New-ADOrganizationalUnit -Name $ou.Name -Path $ou.Path -Description $marker -ProtectedFromAccidentalDeletion $true
        $createdOus++
    }
}
foreach($group in $groups) {
    $name=$group.Name
    if(-not (Get-ADGroup -Filter "SamAccountName -eq '$name'")) {
        New-ADGroup -Name $name -SamAccountName $name -GroupScope $group.Scope -GroupCategory Security -Path "OU=Groups,$root" -Description $marker
        $createdGroups++
    }
}
foreach($link in $links) {
    $member=Get-ADGroup $link.Member
    $target=Get-ADGroup $link.Target -Properties Members
    if($member.DistinguishedName -notin $target.Members) {
        Add-ADGroupMember -Identity $target -Members $member
        $addedLinks++
    }
}
[ordered]@{CreatedOus=$createdOus; CreatedGroups=$createdGroups; AddedGroupLinks=$addedLinks; FilePermissionsConfigured=$false; UserAccountsCreated=0} | ConvertTo-Json
