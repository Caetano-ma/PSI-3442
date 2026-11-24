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

builtin_interfaces/Time stamp
uint8 tarefa
string tipo
string estado
int8 vertice
string nome_vertice
float64 permanencia_s
uint8 acao                      # ComandoDiscreto.tipo quando tipo = SOLICITA_ACAO
float64 valor
string detalhe
