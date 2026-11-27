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

---

# Ensaios da Tarefa 2 (Questão 2) — só depois de T01–T04 aprovados em voo real

Casos de verificação V01–V10 em `modelo_sysml/04_Verificacao.sysml`. Os cenários de falha que podem comprometer o
equipamento ficam na simulação (`ensaios/simulacao/`) e nos testes sem voo.

## S1 — Em solo, motores desligados (aeronave ligada, app em "Iniciar (dji)")

1. **Vídeo:** o painel mostra o alvo da visão a ~5 Hz. No log do nó ponte, conferir:
   - a resolução do quadro;
   - o aviso de gimbal, se o pitch passar de 3°.

   Com um balão a 1,00 m medido com trena à frente da câmera, `/alvos.distancia_m` deve dar 1,00 ± 0,10 m.
   Se não der, ajustar `visao.hfov_graus` (campo de visão do fluxo) e registrar o valor.
2. **Proximidade:** com o balão a 0,20 m da câmera (gabarito de papelão), `distancia_central_m` deve dar 0,20 ± 0,01 m.
3. **Obstáculos:** com um anteparo a 1,00 m à frente e depois à direita, conferir em `/dji/obstaculos`:
   - a unidade (m);
   - a origem (0° = nariz);
   - o sentido (o ângulo da direita deve ser negativo no LaserScan).
4. **Raio do balão:** medir o diâmetro horizontal dos balões da prova e ajustar `tarefa2.raio_balao_m`.

## S2 — Um balão-alvo (V03, V04), em voo

- **Preparação:**
  - um balão vermelho fixo a ~1,5 m de altura, a ≥ 1,2 m da decolagem;
  - câmera de validação fixa ao lado (celular, 30 quadros/s), perpendicular ao eixo de aproximação;
  - régua milimetrada no plano vertical do balão.
- **Comando:** `executar tarefa 2` (config com `cores_alvo: [vermelho]`).
- **Aceita se:**
  - `BALAO_DESTRUIDO` com 60 s contínuos em tempo real;
  - no vídeo lateral, a folga entre a frente das hélices e o balão fica em 0 < d ≤ 5 cm durante toda a contagem
    (medida quadro a quadro);
  - nenhum contato;
  - retorno e pouso.
- **Registrar:**
  - d estimada (`/tarefa/evento`, CSV);
  - d medida no vídeo;
  - o erro de estimação na aproximação.

## S3 — Múltiplos alvos e cores não alvo (V03, V06)

- **Preparação:** dois balões-alvo e um não alvo, a ≥ 1,1 m entre centros.
- **Aceita se:**
  - cada alvo é destruído uma vez;
  - nenhum `ALVO_SELECIONADO` de cor não alvo;
  - a folga ao não alvo fica > 0,50 m (vídeo).

## S4 — Reinício da contagem (V04)

Durante a permanência do S2, um auxiliar afasta o balão 10 cm com uma vara.

- **Aceita se:**
  - `PERMANENCIA_INTERROMPIDA` registrada;
  - o drone segue o balão (reancoragem) ou volta à faixa;
  - nova contagem de 60 s contínuos.

## Encerramento da Tarefa 2

O mesmo da Tarefa 1, mais:
- `analisar_ensaio.py` sobre o CSV, para o tempo contínuo por balão, os reinícios e os descartes;
- os vídeos laterais com a marcação dos quadros medidos.
