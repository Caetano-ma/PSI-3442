# Um balão detectado num quadro da câmera (visão computacional, Tarefa 2).
string cor                      # vermelho, azul, verde, amarelo, roxo
float32 confianca               # 0..1 (saída do modelo)
int32 u                         # centro da caixa (px)
int32 v
int32 largura_px
int32 altura_px
float64 azimute_graus           # direção do centro no ReferencialLocal (anti-horária a partir de +x)
float64 elevacao_graus          # acima da horizontal
float64 distancia_m             # câmera -> centro do balão, pelo diâmetro aparente (estimativa)
bool cortada                    # caixa tocando a borda da imagem: distância pouco confiável
