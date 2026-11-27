# Roteiro dos ensaios em voo — Tarefa 1 (Questão 1)

Critérios de aceitação: valores de P05 em `modelo_sysml/03_NivelN.sysml` (`configTarefa1`), aprovados pelos docentes
antes da demonstração e não ampliados depois. Todos os ensaios usam o mesmo arquivo de configuração e geram um bag
(rosbag2) e um CSV por execução.

## Preparação (comum a T01–T04)

1. Marcar no piso, com fita, os pontos A, B, C e D (quadrado de 1,50 m) e uma seta em A apontando para B.
2. Cobrir a área sob a trajetória com superfície texturizada (tapete ou fitas cruzadas) e garantir iluminação
   uniforme; desligar ventiladores e ar-condicionado direcionados.
3. Fixar uma régua vertical (ou fita graduada na parede/tripé) ao lado de A, com marcas em 1,70 m, 1,80 m e 1,90 m,
   no plano da câmera lateral.
4. Posicionar duas câmeras de vídeo: lateral (régua e altura) e superior ou diagonal (marcas do piso). Iniciar as
   gravações e mostrar à câmera um cronômetro sincronizado com o relógio do notebook.
5. Aeronave sobre A, nariz apontado para B. Ligar a aeronave e o controle (RC-N2/RC-N3). Ligar o celular ao controle
   pelo cabo e abrir o app ponte (variante `celular`), modo "dji"; o celular e o notebook ficam na mesma rede Wi-Fi
   (ou o notebook no ponto de acesso do celular). O app mostra o IP do celular.
6. No notebook: `ros2 launch psi3442_tarefas sistema.launch.py host_ponte:=<IP do celular>`; conferir no painel:
   ponte conectada, bateria ≥ 30 %, posicionamento visual ativo, ação em perda de sinal = pousar.
7. Ninguém dentro do volume de voo (2,5 m × 2,5 m × 2,5 m). Operador ao notebook, com o comando "interromper" pronto.

## T00 — Teste de eixos (antes do primeiro T01, e depois de qualquer mudança no app ponte)

- Só o app ponte e o script, **sem** o sistema ROS 2: `python3 ensaios/teste_eixos.py --host <IP do celular>`.
- O script decola, anda 0,2 m/s para a frente e depois para a esquerda (2 s cada) e pousa; Ctrl+C manda pousar.
- Aceita se: o script indica telemetria coerente com o comando (diferença de rumo < 30°) **e** o operador viu a
  aeronave ir para a frente (direção do nariz) e depois para a esquerda.
- Se falhar: corrigir `DroneDji.ROLL_E_NORTE` (troca norte/leste no controle virtual) ou o referencial da velocidade
  e repetir. Nenhum T01–T04 antes de o T00 passar.

## T01 — Altura de decolagem (P01)

- Comando: `executar tarefa 1`.
- Medida interna: `z_m` no CSV entre o evento `AlturaAtingida` e o início da permanência em A.
- Medida externa: altura do plano inferior do corpo da aeronave lida na régua, no vídeo lateral.
- Aceita se: |z − 1,80 m| ≤ 0,10 m nas duas medidas. Registrar o erro interno, o externo e a diferença entre eles.

## T02 — Quadrado horizontal (P02)

- Mesmo voo do T01.
- Medida interna: `x_m`, `y_m`, `z_m` durante cada permanência e durante os deslocamentos.
- Medida externa: posição da projeção da aeronave sobre as marcas do piso no vídeo superior/diagonal.
- Aceita se: erro horizontal ≤ 0,30 m em A, B, C e D; erro vertical ≤ 0,10 m em todo o percurso.
- Registrar: erro em cada vértice, erro de fechamento (posição estimada × posição real ao retornar a A) e a diferença
  entre estimativa e medida externa (deriva da estimação).

## T03 — Permanências de 60 s (P03)

- Mesmo voo do T01.
- Medida: intervalos contínuos com `dentro = true` por vértice (colunas `vertice`, `permanencia_s`, `evento`).
- Aceita se: quatro intervalos ≥ 60 s em tempo real, na ordem A, B, C, D (ou A, D, C, B), sem segunda espera em A.
- Registrar: início, interrupções (reinícios da contagem) e duração final de cada permanência.

## T04 — Pouso suave (P04)

- Mesmo voo do T01.
- Medida: `vz_mps` no instante em que `emVoo` passa a falso; evento `PousoConfirmado`; posição final da aeronave em
  relação à marca de A (vídeo).
- Aceita se: |vz| ≤ 0,50 m/s no toque, pouso a até 0,30 m de A e `PousoConfirmado` registrado antes do fim da tarefa.

## Encerramento

1. Exportar o CSV do bag (`ros2_ws/src/psi3442_tarefas/ferramentas/exportar_csv.py`).
2. Arquivar bag, CSV e vídeos com a data, a versão do código (commit) e o arquivo de configuração usado.
3. Ensaios que falharem são mantidos e reportados; tolerâncias não são alteradas depois do ensaio.
