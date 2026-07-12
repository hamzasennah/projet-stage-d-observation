$ErrorActionPreference = "Stop"

# ==========================
# Configuration
# ==========================
$ProjectRoot = "C:\Users\pc\Desktop\projet-stage-d-observation"
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

$BackendPort = 8002
$FrontendPort = 5173

$OllamaBaseUrl = "http://localhost:11434"
$GenerationModel = "qwen2.5:3b"
$EmbeddingModel = "qwen3-embedding:0.6b"

$StartedProcesses = @()

# ==========================
# Fonctions utilitaires
# ==========================

function Cleanup {
    Write-Host "`nNettoyage des processus lancés..." -ForegroundColor Yellow

    foreach ($proc in $StartedProcesses) {
        try {
            if ($proc -and -not $proc.HasExited) {
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }

    foreach ($port in @($BackendPort, $FrontendPort)) {
        try {
            $connections = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
            foreach ($conn in $connections) {
                try {
                    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                } catch {}
            }
        } catch {}
    }
}

function Fail($Message) {
    Write-Host "`nERREUR : $Message" -ForegroundColor Red
    Cleanup
    exit 1
}

function RequireCommand($CommandName) {
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        Fail "La commande '$CommandName' est introuvable."
    }
}

function WaitUrl($Url, $Name, $TimeoutSeconds = 60) {
    Write-Host "Vérification de $Name : $Url"

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Host "$Name fonctionne." -ForegroundColor Green
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    Fail "$Name ne répond pas sur $Url"
}

function KillPort($Port) {
    Write-Host "Vérification du port $Port..."

    $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)

    if ($connections.Count -eq 0) {
        Write-Host "Port $Port libre." -ForegroundColor Green
        return
    }

    foreach ($conn in $connections) {
        $pidToKill = $conn.OwningProcess

        try {
            $proc = Get-Process -Id $pidToKill -ErrorAction Stop
            Write-Host "Port $Port occupé par $($proc.ProcessName), PID $pidToKill. Arrêt..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction Stop
            Start-Sleep -Seconds 1
        } catch {
            Fail "Impossible d'arrêter le processus PID $pidToKill sur le port $Port."
        }
    }

    $remaining = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)

    if ($remaining.Count -gt 0) {
        Fail "Le port $Port est encore occupé."
    }

    Write-Host "Port $Port libéré." -ForegroundColor Green
}

# ==========================
# Début du script
# ==========================

Write-Host "Démarrage automatique du projet Resume Ranking RAG" -ForegroundColor Cyan

if (-not (Test-Path $ProjectRoot)) {
    Fail "Le dossier du projet est introuvable : $ProjectRoot"
}

if (-not (Test-Path $BackendDir)) {
    Fail "Le dossier backend est introuvable."
}

if (-not (Test-Path $FrontendDir)) {
    Fail "Le dossier frontend est introuvable."
}

# ==========================
# Vérification des commandes
# ==========================

RequireCommand "ollama"
RequireCommand "python"
RequireCommand "pnpm"

# ==========================
# Vérifier Ollama
# ==========================

Write-Host "`nVérification de Ollama..." -ForegroundColor Cyan

try {
    Invoke-WebRequest -Uri "$OllamaBaseUrl/api/version" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Write-Host "Ollama répond déjà." -ForegroundColor Green
} catch {
    Write-Host "Ollama ne répond pas. Tentative de lancement..." -ForegroundColor Yellow

    try {
        $ollamaProc = Start-Process -FilePath "ollama" -ArgumentList "serve" -PassThru -WindowStyle Minimized
        $StartedProcesses += $ollamaProc
        Start-Sleep -Seconds 5
    } catch {
        Fail "Impossible de lancer Ollama."
    }
}

WaitUrl "$OllamaBaseUrl/api/version" "Ollama" 30

# ==========================
# Vérifier les modèles Ollama
# ==========================

Write-Host "`nVérification des modèles Ollama..." -ForegroundColor Cyan

$ollamaList = (ollama ls) -join "`n"

if ($ollamaList -notmatch [regex]::Escape($GenerationModel)) {
    Fail "Modèle de génération introuvable : $GenerationModel. Lance d'abord : ollama pull $GenerationModel"
}

if ($ollamaList -notmatch [regex]::Escape($EmbeddingModel)) {
    Fail "Modèle embedding introuvable : $EmbeddingModel. Lance d'abord : ollama pull $EmbeddingModel"
}

Write-Host "Modèles Ollama trouvés." -ForegroundColor Green

# ==========================
# Créer / corriger les fichiers .env
# ==========================

Write-Host "`nConfiguration des fichiers .env..." -ForegroundColor Cyan

$RootEnvContent = @"
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=$OllamaBaseUrl
OLLAMA_GENERATION_MODEL=$GenerationModel
OLLAMA_EMBEDDING_MODEL=$EmbeddingModel
CHROMA_PATH=data/chroma
VITE_API_URL=http://127.0.0.1:$BackendPort
"@

Set-Content -Path (Join-Path $ProjectRoot ".env") -Value $RootEnvContent -Encoding UTF8

$FrontendEnvContent = @"
VITE_API_URL=http://127.0.0.1:$BackendPort
"@

Set-Content -Path (Join-Path $FrontendDir ".env") -Value $FrontendEnvContent -Encoding UTF8

Write-Host ".env configurés." -ForegroundColor Green

# ==========================
# Vérifier dépendances backend
# ==========================

Write-Host "`nVérification backend Python..." -ForegroundColor Cyan

$PythonCommand = "python"

$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
}

Push-Location $BackendDir
& $PythonCommand -c "import uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Fail "uvicorn n'est pas installé. Lance : pip install -r requirements-dev.txt"
}
Pop-Location

Write-Host "Backend Python OK." -ForegroundColor Green

# ==========================
# Vérifier dépendances frontend
# ==========================

Write-Host "`nVérification frontend..." -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "node_modules introuvable. Installation pnpm..." -ForegroundColor Yellow

    Push-Location $FrontendDir
    pnpm install

    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Fail "pnpm install a échoué."
    }

    Pop-Location
}

Write-Host "Frontend OK." -ForegroundColor Green

# ==========================
# Libérer les ports
# ==========================

Write-Host "`nLibération des ports..." -ForegroundColor Cyan

KillPort $BackendPort
KillPort $FrontendPort

# ==========================
# Lancer backend
# ==========================

Write-Host "`nLancement du backend..." -ForegroundColor Cyan

$BackendCommand = "cd `"$BackendDir`"; `"$PythonCommand`" -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload"

$BackendProc = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $BackendCommand -PassThru
$StartedProcesses += $BackendProc

WaitUrl "http://127.0.0.1:$BackendPort/api/health" "Backend FastAPI" 60

# ==========================
# Lancer frontend
# ==========================

Write-Host "`nLancement du frontend..." -ForegroundColor Cyan

$FrontendCommand = "cd `"$FrontendDir`"; pnpm run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort"

$FrontendProc = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $FrontendCommand -PassThru
$StartedProcesses += $FrontendProc

WaitUrl "http://127.0.0.1:$FrontendPort" "Frontend Vite" 60

# ==========================
# Ouvrir le site
# ==========================

Write-Host "`nApplication lancée avec succès." -ForegroundColor Green
Write-Host "Frontend : http://127.0.0.1:$FrontendPort"
Write-Host "Backend  : http://127.0.0.1:$BackendPort/api/health"

Start-Process "http://127.0.0.1:$FrontendPort"

Write-Host "`nNe ferme pas les fenêtres backend/frontend pendant l'utilisation." -ForegroundColor Yellow