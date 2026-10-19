[CmdletBinding()]
param(
    [switch]$SkipImageBuild
)

$ErrorActionPreference = "Stop"
$clusterName = "music-app"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$kindConfig = Join-Path $root "kind-config.yml"
$sambaCompose = Join-Path $root "samba\docker-compose-samba.yml"
$ingressPatch = Join-Path $root "ingress-controller-patch.json"

function Invoke-CommandChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

Set-Location $root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not available. Start Docker Desktop and try again."
}
if (-not (Get-Command kind -ErrorAction SilentlyContinue)) {
    throw "kind is not available. Install kind and try again."
}
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl is not available. Install kubectl and try again."
}
if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
    throw "helm is not available. Install Helm before setting up Redis Sentinel."
}

$clusters = @(kind get clusters 2>$null)
if ($clusters -notcontains $clusterName) {
    Invoke-CommandChecked "Create KinD cluster" {
        kind create cluster --config $kindConfig
    }
} else {
    Write-Host "`n==> KinD cluster '$clusterName' already exists; skipping creation." -ForegroundColor Yellow
}

Invoke-CommandChecked "Start local Samba share" {
    docker compose -f $sambaCompose up -d --build
}

$version = "v1.18.0"
$base = "https://raw.githubusercontent.com/kubernetes-csi/csi-driver-smb/$version/deploy/$version"
Invoke-CommandChecked "Install SMB CSI RBAC" {
    kubectl apply -f "$base/rbac-csi-smb.yaml"
}
Invoke-CommandChecked "Install SMB CSI driver objects" {
    kubectl apply -f "$base/csi-smb-driver.yaml"
}
Invoke-CommandChecked "Install SMB CSI controller" {
    kubectl apply -f "$base/csi-smb-controller.yaml"
}
Invoke-CommandChecked "Install SMB CSI node plugin" {
    kubectl apply -f "$base/csi-smb-node.yaml"
}
Invoke-CommandChecked "Wait for SMB CSI controller" {
    kubectl wait --namespace kube-system --for=condition=ready pod --selector=app=csi-smb-controller --timeout=180s
}

Invoke-CommandChecked "Install NGINX Ingress controller" {
    kubectl apply -f "https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"
}
Invoke-CommandChecked "Wait for NGINX Ingress controller" {
    kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s
}
Invoke-CommandChecked "Pin NGINX Ingress to the port-mapped node" {
    kubectl patch deployment ingress-nginx-controller --namespace ingress-nginx --type=merge --patch-file $ingressPatch
}
Invoke-CommandChecked "Wait for NGINX Ingress rollout" {
    kubectl rollout status deployment/ingress-nginx-controller --namespace ingress-nginx --timeout=120s
}

Invoke-CommandChecked "Create music-app namespace" {
    kubectl create namespace music-app --dry-run=client -o yaml | kubectl apply -f -
}

Invoke-CommandChecked "Add Bitnami Helm repository" {
    helm repo add bitnami https://charts.bitnami.com/bitnami --force-update
}
Invoke-CommandChecked "Update Bitnami Helm repository" {
    helm repo update bitnami
}
Invoke-CommandChecked "Install Redis Sentinel" {
    helm upgrade --install redis bitnami/redis --namespace music-app --create-namespace --values ".\redis\redis-values.yml"
}
Invoke-CommandChecked "Wait for Redis Sentinel StatefulSet" {
    kubectl rollout status statefulset/redis-node --namespace music-app --timeout=300s
}

$images = @(
    @{ Name = "andriuskl/catalog-svc_1:3.0.1"; Context = ".\catalog-svc" },
    @{ Name = "andriuskl/shop-front-svc:3.0.1"; Context = ".\shop-front-svc" },
    @{ Name = "andriuskl/product-admin-svc:3.0.1"; Context = ".\product-admin-svc" },
    @{ Name = "andriuskl/song-player-svc:3.0.1"; Context = ".\song-player-svc" },
    @{ Name = "andriuskl/history-svc:3.0.1"; Context = ".\history-svc" },
    @{ Name = "andriuskl/login-page-svc:3.0.1"; Context = ".\login-page-svc" }
)

foreach ($image in $images) {
    if (-not $SkipImageBuild) {
        Invoke-CommandChecked "Build $($image.Name)" {
            docker build -t $image.Name $image.Context
        }
    }
    Invoke-CommandChecked "Load $($image.Name) into KinD" {
        kind load docker-image $image.Name --name $clusterName
    }
}

Invoke-CommandChecked "Deploy music application" {
    kubectl apply -k ".\base\dev"
}

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "Check status with: kubectl get pods -A"
Write-Host "Open: http://localhost/get-catalog"
