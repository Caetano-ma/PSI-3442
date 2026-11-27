# /mapa — mapa grosseiro da sala: balões e grade 2D de ocupação (obstáculos vistos pela aeronave).
builtin_interfaces/Time stamp
BalaoMapa[] baloes
float32 resolucao_m
uint16 largura                  # células em x
uint16 altura                   # células em y
float64 origem_x_m              # canto (x mínimo, y mínimo) da grade
float64 origem_y_m
int8[] ocupacao                 # -1 desconhecido, 0 livre, 100 ocupado; linha a linha (y), da origem
