# /alvos — detecções de um quadro da câmera, com a pose estimada da aeronave no instante do quadro.
builtin_interfaces/Time stamp
float64 x_m                     # pose estimada da aeronave no ReferencialLocal
float64 y_m
float64 z_m
float64 guinada_local_graus
DeteccaoBalao[] deteccoes
string cor_central              # cor dominante no centro da imagem (curta distância), "" se nenhuma
float32 fracao_cor_central      # fração dos pixels do centro com essa cor
float32 distancia_central_m         # câmera -> centro do balão da cor central, pela largura; NaN se não mensurável;
                                    # negativa (-D) se cortado pela borda: a distância é no máximo D
float32 azimute_central_graus       # azimute desse centro no ReferencialLocal
