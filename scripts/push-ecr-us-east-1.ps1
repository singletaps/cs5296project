#Requires -Version 5.1
<#
  Build converter image, tag for ECR, login, push to us-east-1.
  Prerequisites:
  - Docker Desktop running
  - AWS credentials (aws configure, or env AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, or SSO)
  - EITHER: AWS Tools for PowerShell (Install-Module AWS.Tools.ECR)
  - OR:     python -m awscli (pip install awscli)

  Usage (from repo root):
    .\scripts\push-ecr-us-east-1.ps1
#>
$ErrorActionPreference = 'Stop'

$AccountId    = '161748405735'
$Region       = 'us-east-1'
$RepoName     = 'cs5296project'
$LocalTag     = 'cs5296project:latest'
$RegistryHost = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$RemoteImage  = "$RegistryHost/${RepoName}:latest"

$RepoRoot     = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ConverterDir = Join-Path $RepoRoot 'services\converter'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw 'Docker not found. Install Docker Desktop and ensure it is running.'
}

Write-Host "[1/4] Building image in services\converter ..."
Push-Location $ConverterDir
try {
  docker build -t $LocalTag .
  if ($LASTEXITCODE -ne 0) { throw "docker build failed with exit $LASTEXITCODE" }
} finally {
  Pop-Location
}

Write-Host "[2/4] Tagging -> $RemoteImage"
docker tag $LocalTag $RemoteImage
if ($LASTEXITCODE -ne 0) { throw "docker tag failed" }

Write-Host "[3/4] ECR login ($RegistryHost) ..."
$loginOk = $false

# Method A: AWS Tools for PowerShell (user-requested)
if (-not (Get-Command Get-ECRLoginCommand -ErrorAction SilentlyContinue)) {
  Import-Module AWS.Tools.ECR -ErrorAction SilentlyContinue
}
if (Get-Command Get-ECRLoginCommand -ErrorAction SilentlyContinue) {
  try {
    (Get-ECRLoginCommand -Region $Region).Password | docker login --username AWS --password-stdin $RegistryHost
    if ($LASTEXITCODE -eq 0) { $loginOk = $true }
  } catch {
    Write-Warning "Get-ECRLoginCommand failed: $_"
  }
}

# Method B: AWS CLI via pip (python -m awscli)
if (-not $loginOk) {
  $py = Get-Command python -ErrorAction SilentlyContinue
  if ($py) {
    & python -m awscli ecr get-login-password --region $Region 2>$null | docker login --username AWS --password-stdin $RegistryHost
    if ($LASTEXITCODE -eq 0) { $loginOk = $true }
  }
}

if (-not $loginOk) {
  throw @"
ECR login failed. Configure credentials, then retry:
  aws configure
or set environment variables / use AWS SSO.
Install one of:
  Install-Module -Name AWS.Tools.ECR -Scope CurrentUser -Force
  pip install awscli   (then: python -m awscli configure)
"@
}

Write-Host "[4/4] Pushing $RemoteImage ..."
docker push $RemoteImage
if ($LASTEXITCODE -ne 0) { throw "docker push failed (create ECR repo '$RepoName' in $Region if missing)" }

Write-Host "Done. Image: $RemoteImage"
