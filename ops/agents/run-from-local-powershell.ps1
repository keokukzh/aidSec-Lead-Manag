$ErrorActionPreference = 'Stop'

# Run from your local Windows PowerShell
# Assumes you can SSH as root to both hosts.

$repo = 'C:/Users/aidevelo/Desktop/aidSec-Lead-Manag'
$script1 = "$repo/ops/agents/setup-agent1-100.88.218.9.sh"
$script2 = "$repo/ops/agents/setup-agent2-100.87.63.92.sh"

Write-Host 'Uploading + running setup on agent1 (100.88.218.9)...'
(Get-Content -Raw $script1) | ssh root@100.88.218.9 "tr -d '\r' | bash -s"

Write-Host 'Uploading + running setup on agent2 (100.87.63.92)...'
(Get-Content -Raw $script2) | ssh root@100.87.63.92 "tr -d '\r' | bash -s"

Write-Host 'Running queue trigger once on agent1...'
ssh root@100.88.218.9 '/usr/local/bin/aidsec-queue-trigger.sh || true'

Write-Host 'Done. Checking API pull endpoint for both agents...'
$base = 'https://aidsec-lead-manag-production-7292.up.railway.app/api'
$globalApiKey = 'aidsec_api_a4da3c7956334a7b94d3c2e374e69961'
$agent1Key = 'agt1_41fcf33f3b5240cf9bb9cf0d1154ff71'
$agent2Key = 'agt2_5aea9e57cb08417b9e64888b1ef14a87'

try {
  $r1 = curl.exe -sS -i -H "Authorization: Bearer $globalApiKey" -H "X-API-Key: $agent1Key" "$base/agents/tasks/pull?agent_id=agent1&lease_seconds=120"
  Write-Host "agent1 pull response:`n$r1"
} catch {
  Write-Host "agent1 pull error: $($_.Exception.Message)"
}

try {
  $r2 = curl.exe -sS -i -H "Authorization: Bearer $globalApiKey" -H "X-API-Key: $agent2Key" "$base/agents/tasks/pull?agent_id=agent2&lease_seconds=120"
  Write-Host "agent2 pull response:`n$r2"
} catch {
  Write-Host "agent2 pull error: $($_.Exception.Message)"
}

Write-Host 'Done.'
