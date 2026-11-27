# /setpoint — ponto desejado no ReferencialLocal (10 Hz, best effort).
# ativo = false: nenhum comando de velocidade deve ser enviado (decolagem e pouso automáticos da DJI).
builtin_interfaces/Time stamp
bool ativo
float64 x_m
float64 y_m
float64 z_m
int8 indice
string nome
bool guinada_ativa              # true: o controle também leva a guinada a guinada_graus
float64 guinada_graus           # guinada no ReferencialLocal (anti-horária a partir de +x)
