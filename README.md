# Windows identity lab — readiness tools

This is the first implemented part of a planned, isolated Windows administration lab. **The Active Directory lab is not deployed or verified yet.** These tools check a fictional lab configuration and the host's current resources without changing VMs, accounts, networking or security settings.

## Run the checks

Python 3.11+ and Windows PowerShell are enough. There are no Python package dependencies.

```powershell
# Keep the actual host report outside the repository.
& .\tools\Get-LabInventory.ps1 | Set-Content -Encoding utf8 ..\lab-inventory-private.json
python .\tools\check_readiness.py --inventory ..\lab-inventory-private.json
python -m unittest discover -s tests -v
```

If Windows blocks an unsigned script, do not weaken execution policy. Review it and run its read-only commands interactively, or use your normal approved script-signing process.

Exit codes: 0 means the resource gate passed, 1 means prerequisites are blocked, and 2 means invalid input. A passing resource check **does not** verify guest licensing, hypervisor compatibility, a working domain or safe deployment. Reports older than 15 minutes are rejected. The utility does not install or start anything.

The configuration reserves 50 GiB for the DC, 64 GiB for the client, 16 GiB for media/staging and 40 GiB for the host: 170 GiB free required. It also requires 12 GiB currently available memory. These are conservative project choices, not vendor minimums. Dynamic disks do not remove the need to budget for growth.

To check whether there is room to install just the Server guest first:

```powershell
python .\tools\check_readiness.py --inventory ..\lab-inventory-private.json --scope server-install
```

That stage needs 106 GiB free disk and 8 GiB available RAM with the supplied configuration. It keeps the same host and media reserves and budgets the Server disk's full possible size. A stage passing does not mean there is room for both guests. Collect fresh measurements and reassess before adding the client, running guests together or taking backups. These checks budget new allocations; they do not subtract disks or RAM already allocated to an existing guest, monitor growth, or start a VM. Keep at least 40 GiB free on the host during installation. The default remains the full Project 1 check.

Only `ad.northstar.test`, two named lab guests and an internal network are accepted. This intentionally prevents using the readiness tool as a generic production deployment tool. Existing VMs are outside its scope.

## Prepare the Server guest

`tools/Initialize-LabServer.ps1` runs **inside a fresh, standalone Server VM**, as its Administrator. First verify in VirtualBox that its only adapter uses the internal `rh-identity-lab` network. Get that VM's hardware UUID with `VBoxManage showvminfo`; pass it as `-ExpectedVmUuid` when running the script. Start with `-WhatIf` to review the action, then run without `-WhatIf` to apply it.

The script refuses a different UUID, a non-VirtualBox machine, a Windows client, a domain member, multiple/disconnected adapters, default routes or unexpected IP addresses. Guest checks cannot prove the hypervisor's network mode: the host-side isolation check is still required. It configures `10.77.0.10/24`, DNS pointing to itself, the name `RH-LAB-DC01`, and the AD DS/DNS/Group Policy management components. It leaves IPv6 and the firewall enabled. It does not create a domain or restart automatically. Restart only this guest afterward.

Audit stages are recorded in `C:\ProgramData\NorthstarLab\Logs\server-bootstrap.jsonl`. Failure stops the script but can leave partial changes; inspect the log and actual network/features before retrying. There is no automatic rollback. Return to a verified pre-install backup or rebuild this dedicated disposable guest if needed; never apply teardown to another VM.

## Remaining lab work

Lawful Windows guest media and license acceptance, enough resources, a verified guest boot, AD/DNS/GPO setup, lifecycle automation, real access tests, five observed support cases, and backup/restore verification. The connected SIEM project must wait until those Project 1 checks pass. No real credentials or host logs belong in this repository.
