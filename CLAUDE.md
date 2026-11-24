# PSI3442 — P2 2026 — Sistema de Missões Autônomas com DJI Mini 4 Pro

Contexto para continuar o trabalho em outra máquina. Responder sempre em **português**.

## O projeto

Segunda prova de PSI3442 (Projeto de Sistemas Embarcados, Poli-USP), enunciado v2.5 de 15/11/2026
(`P2_PSI3442_2026_v2_5.docx`, **fora do repositório** por ser documento do professor — pedir ao usuário se precisar).
Duas questões, chamadas aqui de tarefas:

- **Tarefa 1** (Questão 1, P01–P06): decolar a 1,80 m, quadrado A-B-C-D de 1,50 m, pairar 60 s contínuos em cada
  vértice, voltar a A e pousar suavemente. Precisa ser demonstrada em voo real antes da Tarefa 2.
- **Tarefa 2** (Questão 2, R01–R09): identificar balões de cores-alvo e permanecer a 0 < d ≤ 5 cm por 60 s.

Prazos: entrega intermediária **27/11/2026** (pronta em `entregas/2026-11-27_intermediaria/`); entrega final e
demonstração em voo real **04/12/2026**. Equipe: Caetano Maciel Anibali (13681130); outros integrantes talvez depois.

## Arquitetura decidida (não mudar sem o usuário pedir)

- O drone é dado; o problema é de **software**. O alvo da decomposição são as **tarefas**; drone e rádio são caixas-pretas.
- **Notebook Linux com ROS 2 Jazzy** (Mint 22 / Ubuntu 24.04) roda toda a lógica em nós ROS 2 (Python/rclpy):
  interface do operador, gerenciador de tarefas, Tarefa 1, Tarefa 2, estimação de estado, controle de voo, supervisão
  e segurança, registro (rosbag2 + CSV), percepção visual (T2), mapeamento local grosseiro (T2), nó ponte ROS 2 ↔ DJI.
- **Android emulado** no notebook roda o *app ponte* em Kotlin com o **DJI Mobile SDK v5**; fala com o ROS 2 por TCP
  (adb forward, porta 5760, JSON por linha, heartbeat). Alternativa se o emulador falhar: o celular Android da equipe.
- O operador só envia `executar tarefa 1`, `executar tarefa 2` ou `interromper`; ninguém pilota.
- **Controle remoto:** verificado nas notas do MSDK v5 que o Mini 4 Pro só funciona com **DJI RC N2 ou RC N3**
  (SDK ≥ 5.13.0; atual 5.20.1); DJI RC 2 não é suportado e não há conexão direta celular ↔ drone. O usuário diz não ter
  controle → hipótese H7: o kit do laboratório tem um (confirmar com os docentes). É o maior bloqueio do projeto.
- Sem GNSS em ambiente interno: posição = integração das velocidades do posicionamento visual da DJI (deriva é risco);
  altura = sensor ToF. Referencial local: origem em A no piso, x para B, y para D, z para cima.
- P05 aprovado pelo usuário: ±0,10 m vertical, ±0,30 m horizontal, 0,15 m/s para "pairado", 0,50 m/s no toque.
- Balões da Tarefa 2: estáticos (forma de fixação irrelevante).

## Estrutura e comandos

| Caminho | Conteúdo |
|---|---|
| `diagramas/gerar_diagramas.py` | Diagramas funcionais de nível 0 e 1 (estilo dos diagramas do usuário) → `nivel_0.png`, `nivel_1.png` |
| `modelo_sysml/00_Comum.sysml` … `04_Verificacao.sysml` | Modelo SysML 2.0: tipos/tópicos/requisitos, nível 0, nível 1, nível n, casos de verificação |
| `modelo_sysml/executar_modelo.py` | Valida o modelo no kernel SysML e exporta 14 vistas para `vistas/`; gera `Modelo.ipynb` |
| `modelo_sysml/gerar_matriz.py` | Matriz de rastreabilidade da Tarefa 1 + checagem de consistência entre níveis (sai com erro se houver furo) |
| `modelo_sysml/abrir_jupyter.sh` | Abre o modelo no JupyterLab |
| `ensaios/roteiro_voo_tarefa1.md` | Procedimentos dos ensaios em voo T01–T04 |
| `entregas/2026-11-27_intermediaria/` | `relatorio.md` → `gerar_pdf.py` → `relatorio.pdf` + ZIP do Moodle |
| `ambiente/instalar_ambiente.sh` | Recria o ambiente conda `sysml` (kernel SysML v2 0.63.1, JupyterLab, weasyprint) |
| `contexto_claude/memoria/` | Memórias do Claude da máquina anterior (ver `contexto_claude/LEIA-ME.md`) |

```bash
bash ambiente/instalar_ambiente.sh                                   # uma vez por máquina
PY=~/miniforge3/envs/sysml/bin/python
cd modelo_sysml && $PY executar_modelo.py && python3 gerar_matriz.py  # depois de editar o modelo
$PY diagramas/gerar_diagramas.py                                      # depois de editar os diagramas
$PY entregas/2026-11-27_intermediaria/gerar_pdf.py                    # regenera PDF e ZIP
```

Pegadinhas do SysML v2 Pilot já encontradas: `interface` é palavra reservada; `flow` não liga o parâmetro da própria
ação (usar `bind`); item dentro de item é `item`, não `attribute`; não nomear partes como o `subject` dos requisitos
(o subject se chama `sujeito`). Visões de interconexão grandes ficam ilegíveis — usar `--view=tree --style=LR`.

## Convenções de trabalho

- **Publicar no GitHub após cada mudança** (https://github.com/Caetano-ma/PSI-3442, branch `main`, público).
  Não alterar o git config. Commit com
  `git -c user.name=Caetano-ma -c user.email=281951699+Caetano-ma@users.noreply.github.com commit ...`
  e push com `git -c credential.helper= -c credential.helper='!gh auth git-credential' push` (requer `gh auth login`).
- Quando o usuário fornecer diagramas/modelos próprios, **adaptar minimamente** (manter blocos, layout e cores);
  ele rejeitou redesenhos do zero.
- Instruções condicionais ("se X estiver errado, aponte e pare") devem ser seguidas literalmente.
- Valores e nomes de API marcados "verificar" no modelo ainda não foram confirmados — não apresentá-los como fatos.

## Pendências (em 24/11/2026)

1. Confirmar com os docentes se o kit tem controle RC-N2/RC-N3 (H7). Sem ele a arquitetura precisa ser revista.
2. Enviar a entrega intermediária (PDF + ZIP) no Moodle; acrescentar outros integrantes se houver.
3. Ciclo C1 (até 29/11): prova de viabilidade da ponte — Android emulado + MSDK (bibliotecas ARM) + controle por USB
   passthrough + ativação da chave do SDK; decidir pela alternativa com celular físico se falhar.
4. Ciclo C2: workspace ROS 2 (`ros2_ws/src/psi3442_interfaces`, `psi3442_tarefas`), nós da Tarefa 1, simulador
   cinemático simples, testes T05, T07, T08, T10. Nada de código existe ainda; ROS 2 Jazzy instalado em `/opt/ros/jazzy`
   na máquina anterior (sem Android SDK/adb/emulador).
5. Ciclo C3: app ponte Kotlin (ConexaoSdk, LeitorTelemetria, EmissorComandos, ConfiguradorSeguranca, ServidorSocket),
   testes em solo, T09, latência.
6. Ciclo C4: voos T01–T04, ajuste do controlador, demonstração da Tarefa 1.
7. Ciclo C5: nível n e implementação da Tarefa 2 (percepção, mapeamento, aproximação), vídeo ≤ 2 min 30 s, README,
   relatório final com 2 páginas de justificativa técnico-econômica e registro do uso de IA.
