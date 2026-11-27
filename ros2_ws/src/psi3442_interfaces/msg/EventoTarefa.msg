# /tarefa/evento — eventos discretos das tarefas (sob demanda, reliable).
string TRANSICAO = "TRANSICAO"                          # estado novo em "estado"
string PERMANENCIA_INICIADA = "PERMANENCIA_INICIADA"
string PERMANENCIA_INTERROMPIDA = "PERMANENCIA_INTERROMPIDA"
string PERMANENCIA_CONCLUIDA = "PERMANENCIA_CONCLUIDA"
string SOLICITA_ACAO = "SOLICITA_ACAO"                  # pede ao gerenciador um comando discreto (campo acao)
string PREPARACAO_FALHOU = "PREPARACAO_FALHOU"
string POUSO_CONFIRMADO = "POUSO_CONFIRMADO"            # valor = |vz| no toque (m/s)
string TAREFA_CONCLUIDA = "TAREFA_CONCLUIDA"
string TAREFA_ABORTADA = "TAREFA_ABORTADA"
# Tarefa 2 (vertice = id do balão no mapa, nome_vertice = "cor#id")
string ALVO_SELECIONADO = "ALVO_SELECIONADO"
string ALVO_DESCARTADO = "ALVO_DESCARTADO"            # não confirmado pela visão no ponto de espera
string ALVO_INALCANCAVEL = "ALVO_INALCANCAVEL"
string COLISAO_ESTIMADA = "COLISAO_ESTIMADA"
string BALAO_DESTRUIDO = "BALAO_DESTRUIDO"            # valor = id; x_m, y_m, z_m = centro medido de perto

builtin_interfaces/Time stamp
uint8 tarefa
string tipo
string estado
int16 vertice                   # Tarefa 1: índice do vértice; Tarefa 2: id do balão
string nome_vertice
float64 permanencia_s
uint8 acao                      # ComandoDiscreto.tipo quando tipo = SOLICITA_ACAO
float64 valor
string detalhe
float64 x_m                     # posição associada ao evento (ReferencialLocal), se houver
float64 y_m
float64 z_m
