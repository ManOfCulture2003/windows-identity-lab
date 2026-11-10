# Verification and limits

November 10 continuation: the Server bootstrap was exercised in a real Windows Server 2025 Standard Evaluation VM. Its dry run reached the expected action without running the mutation block. A deliberately incorrect VM UUID was rejected. The actual run installed AD DS, DNS and the management components; after restarting only the guest, inventory confirmed the name `RH-LAB-DC01`, address `10.77.0.10/24`, DNS `10.77.0.10`, no default routes, and the installed roles. The sanitized observed values are in `evidence/server-bootstrap.json`. The machine was still in WORKGROUP: **a working domain has not been demonstrated**.

All 11 Python resource-check tests passed locally. PowerShell syntax parsing passed. These tests do not exercise role installation; that was checked separately in the guest. Bootstrap error recovery, every rejection path, backup/restore, domain promotion and client joining still need validation. Windows evaluation activation is still pending; the initial grace period is not a permanent license.

The role installation follows Microsoft's [AD DS installation guidance](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/deploy/install-active-directory-domain-services--level-100-). The script deliberately stops before promotion and automatic reboot.

November 9, 2026: nine unittest cases passed locally on Windows/Python 3.12. The PowerShell collector parsed successfully and was exercised read-only on the host. Its resulting resource report correctly returned a blocked status; no VMs or host settings were changed.

Tests cover resource boundaries, missing/unknown/duplicate fields, non-finite and wrongly typed measurements, stale timestamps, incorrect guest identities/addresses, removable volumes and unsafe network modes. The status keeps deployment verification false even when resource checks pass.

CI runs offline tests and PowerShell parsing on Windows and Ubuntu with Python 3.11 and 3.13. It does not prove that Active Directory, DNS, Group Policy or any guest OS works. Check the actual workflow result for the commit being reviewed.

The budget is a planning choice. Windows client requirements and Windows Server guidance should be checked against the exact media before installation:

- https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements
- https://learn.microsoft.com/en-us/windows-server/get-started/hardware-requirements
- https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2025
- https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise

Remaining prerequisites include lawful guest media/license acceptance, sufficient current resources, host/guest compatibility testing and a backup destination. No screenshots of a working domain or closed support tickets are claimed.
