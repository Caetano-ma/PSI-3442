# Balão registrado no mapa local (posição no ReferencialLocal).
uint8 CANDIDATO = 0             # visto poucas vezes
uint8 CONFIRMADO = 1
uint8 DESTRUIDO = 2             # permanência de 60 s concluída: ignorado na varredura
uint16 id
string cor
bool alvo                       # cor em tarefa2.cores_alvo
float64 x_m
float64 y_m
float64 z_m
float64 incerteza_m             # desvio-padrão da posição estimada
uint16 observacoes
uint8 situacao
