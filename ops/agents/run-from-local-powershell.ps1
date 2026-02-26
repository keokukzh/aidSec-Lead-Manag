$ErrorActionPreference = 'Stop'

# Run from your local Windows PowerShell
# Assumes you can SSH as root to both hosts.

$repo = 'C:/Users/aidevelo/Desktop/aidSec-Lead-Manag'
$script1 = "$repo/ops/agents/setup-agent1-100.88.218.9.sh"
$script2 = "$repo/ops/agents/setup-agent2-100.87.63.92.sh"

Write-Host 'Uploading + running setup on agent1 (100.88.218.9)...'
type $script1 | ssh root@100.88.218.9 'bash -s'

Write-Host 'Uploading + running setup on agent2 (100.87.63.92)...'
type $script2 | ssh root@100.87.63.92 'bash -s'

Write-Host 'Done. Checking API pull endpoint for both agents...'
$base = 'https://aidsec-lead-manag-production-7292.up.railway.app/api'
$globalApiKey = 'aidsec_api_a4da3c7956334a7b94d3c2e374e69961'
$agent1Key = 'agt1_41fcf33f3b5240cf9bb9cf0d1154ff71'
$agent2Key = 'agt2_5aea9e57cb08417b9e64888b1ef14a87'

try {
  $r1 = Invoke-WebRequest -Uri "$base/agents/tasks/pull?agent_id=agent1&lease_seconds=120" -Headers @{ Authorization = "Bearer $globalApiKey"; 'X-API-Key' = $agent1Key } -Method GET -TimeoutSec 20
  Write-Host "agent1 pull status: $($r1.StatusCode)"
} catch {
  Write-Host "agent1 pull error: $($_.Exception.Message)"
}

try {
  $r2 = Invoke-WebRequest -Uri "$base/agents/tasks/pull?agent_id=agent2&lease_seconds=120" -Headers @{ Authorization = "Bearer $globalApiKey"; 'X-API-Key' = $agent2Key } -Method GET -TimeoutSec 20
  Write-Host "agent2 pull status: $($r2.StatusCode)"
} catch {
  Write-Host "agent2 pull error: $($_.Exception.Message)"
}
