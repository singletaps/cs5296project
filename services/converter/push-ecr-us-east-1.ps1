# Push converter image to Amazon ECR (us-east-1)
# Prereq: AWS credentials configured (aws configure, SSO, or profile), Docker running.
# Install: AWS CLI v2 OR AWS Tools for PowerShell (AWS.Tools.ECR)

$ErrorActionPreference = "Stop"
$Region = "us-east-1"
$AccountId = "161748405735"
$Repo = "cs5296-project"
$Registry = "${AccountId}.dkr.ecr.${Region}.amazonaws.com"
$ImageLocal = "cs5296-project:latest"
$ImageRemote = "${Registry}/${Repo}:latest"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Building from: $ScriptDir"
docker build -t $ImageLocal .

Write-Host "Tagging: $ImageRemote"
docker tag $ImageLocal $ImageRemote

Write-Host "Logging in to ECR..."
if (Get-Command aws -ErrorAction SilentlyContinue) {
    aws ecr get-login-password --region $Region `
        | docker login --username AWS --password-stdin $Registry
} else {
    Import-Module AWS.Tools.ECR -ErrorAction Stop
    (Get-ECRLoginCommand -Region $Region).Password `
        | docker login --username AWS --password-stdin $Registry
}

Write-Host "Pushing: $ImageRemote"
docker push $ImageRemote

Write-Host "Done. Image: $ImageRemote"
