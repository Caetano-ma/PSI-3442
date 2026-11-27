# /tarefa/status — painel do operador e registro (2 Hz).
builtin_interfaces/Time stamp
string modo                     # ocioso, tarefa1, tarefa2, terminoSeguro
uint8 tarefa                    # 0 = nenhuma
string estado                   # estado da máquina da tarefa (ex.: pairando)
int16 vertice                   # índice na sequência de setpoints (T2: id do balão); -1 = nenhum
string nome_vertice             # A, B, C, D
float64 permanencia_s           # tempo contínuo dentro da tolerância no vértice atual
bool dentro
float64 x_m
float64 y_m
float64 z_m
float64 vx_mps
float64 vy_mps
float64 vz_mps
bool estado_valido
float32 bateria_pct
bool ponte_conectada
bool tarefa1_concluida_voo_real
string ultima_falha
string mensagem                 # resposta ao último comando (aceito/recusado e motivo)
