# Tarefa 1 no Gazebo a partir do Windows (Docker Desktop + WSLg para a janela).
# Uso (PowerShell, na raiz do repositório):
#   .\ros2_ws\docker\simular_gazebo.ps1                         # 60 s por vértice; você comanda pelo operador
#   .\ros2_ws\docker\simular_gazebo.ps1 rapido                  # 5 s por vértice (só simulação)
#   .\ros2_ws\docker\simular_gazebo.ps1 rapido comando_automatico:=true
#   .\ros2_ws\docker\simular_gazebo.ps1 app_args:="--vies-norte 0.01"     # deriva da estimação (H5)
# Depois, em outro PowerShell:
#   docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh          # digite: executar tarefa 1
#   docker exec -it psi3442_gazebo bash /repo/ros2_ws/docker/operador.sh painel
# Bags e CSV ficam em .\simulacoes\ (fora do Git). Ctrl+C encerra e exporta o CSV.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$saida = Join-Path $repo 'simulacoes'
New-Item -ItemType Directory -Force $saida | Out-Null

docker image inspect psi3442-gazebo *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Construindo a imagem psi3442-gazebo (ROS 2 Jazzy + Gazebo Harmonic; só na primeira vez)...'
    docker build -t psi3442-gazebo -f (Join-Path $repo 'ros2_ws\docker\Dockerfile.gazebo') (Join-Path $repo 'ros2_ws\docker')
}
docker rm -f psi3442_gazebo *> $null

docker run --rm -it --name psi3442_gazebo `
    -v "${repo}:/repo:ro" -v "${saida}:/saida" `
    -v /run/desktop/mnt/host/wslg/.X11-unix:/tmp/.X11-unix `
    -v /run/desktop/mnt/host/wslg:/mnt/wslg `
    -e DISPLAY=:0 -e XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir -e QT_QPA_PLATFORM=xcb -e LIBGL_ALWAYS_SOFTWARE=1 `
    psi3442-gazebo bash /repo/ros2_ws/docker/gazebo_tarefa1.sh @args
