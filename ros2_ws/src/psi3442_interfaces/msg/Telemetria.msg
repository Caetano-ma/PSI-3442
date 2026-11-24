# /dji/telemetria — amostra lida pelo app ponte (10 Hz, best effort, profundidade 1).
# stamp = recepção no Linux; instante_android_s = leitura no Android (permite medir latência).
builtin_interfaces/Time stamp
float64 instante_android_s
float64 v_norte_mps
float64 v_leste_mps
float64 v_baixo_mps
float64 altitude_m              # relativa à decolagem (barômetro)
float64 altura_tof_m            # sensor inferior; NaN se indisponível
float64 guinada_graus
bool em_voo
bool motores_ligados
string modo_voo
float32 bateria_pct
bool conectado
bool posicionamento_visual_ativo
bool controle_virtual_ativo
string acao_perda_sinal         # pousar, pairar, retornarAoPonto
