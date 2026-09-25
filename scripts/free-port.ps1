param(
    [Parameter(Mandatory = $true)]
    [int]$Port
)

# netstat can report a dead uvicorn reloader as the owner while its orphaned
# multiprocessing worker still holds the inherited socket, so kill children too.
$ownerIds = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

foreach ($ownerId in $ownerIds) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId = $ownerId" |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Stop-Process -Id $ownerId -Force -ErrorAction SilentlyContinue
}
