# Verification and limits

November 9, 2026: nine unittest cases passed locally on Windows/Python 3.12. The PowerShell collector parsed successfully and was exercised read-only on the host. Its resulting resource report correctly returned a blocked status; no VMs or host settings were changed.

Tests cover resource boundaries, missing/unknown/duplicate fields, non-finite and wrongly typed measurements, stale timestamps, incorrect guest identities/addresses, removable volumes and unsafe network modes. The status keeps deployment verification false even when resource checks pass.

CI runs offline tests and PowerShell parsing on Windows and Ubuntu with Python 3.11 and 3.13. It does not prove that Active Directory, DNS, Group Policy or any guest OS works. Check the actual workflow result for the commit being reviewed.

The budget is a planning choice. Windows client requirements and Windows Server guidance should be checked against the exact media before installation:

- https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements
- https://learn.microsoft.com/en-us/windows-server/get-started/hardware-requirements
- https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2025
- https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise

Remaining prerequisites include lawful guest media/license acceptance, sufficient current resources, host/guest compatibility testing and a backup destination. No screenshots of a working domain or closed support tickets are claimed.
