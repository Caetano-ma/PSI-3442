"""ClienteSocketPonte (nível n): cliente TCP do ContratoSocketPonte.

Protocolo: TCP na porta 5760 (adb forward), mensagens JSON UTF-8, uma por linha, com campo "tipo" em
{telemetria, cmd_vel, acao, heartbeat, erro}. Telemetria a 10 Hz (app -> ROS), cmd_vel a 20 Hz (ROS -> app),
heartbeat a 1 Hz nos dois sentidos. Reconecta automaticamente; a perda da ponte aparece como ausência de
/dji/telemetria e é tratada pela supervisão.
Sem dependência de ROS 2.
"""
import json
import socket
import threading
import time

TIPOS = ('telemetria', 'cmd_vel', 'acao', 'heartbeat', 'erro')
TAMANHO_MAX_LINHA = 64 * 1024


class ErroProtocolo(ValueError):
    pass


def codificar(mensagem):
    if mensagem.get('tipo') not in TIPOS:
        raise ErroProtocolo(f"tipo inválido: {mensagem.get('tipo')!r}")
    return (json.dumps(mensagem, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def decodificar(linha):
    try:
        mensagem = json.loads(linha.decode('utf-8') if isinstance(linha, bytes) else linha)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ErroProtocolo(f'JSON inválido: {erro}') from erro
    if not isinstance(mensagem, dict) or mensagem.get('tipo') not in TIPOS:
        raise ErroProtocolo('mensagem sem campo "tipo" válido')
    return mensagem


class LeitorLinhas:
    """Acumula bytes recebidos e devolve as linhas completas."""

    def __init__(self):
        self._buffer = b''

    def alimentar(self, dados):
        self._buffer += dados
        *linhas, self._buffer = self._buffer.split(b'\n')
        if len(self._buffer) > TAMANHO_MAX_LINHA:
            self._buffer = b''
            raise ErroProtocolo('linha maior que o limite')
        return [linha for linha in linhas if linha.strip()]


class ClienteSocketPonte:
    def __init__(self, host, porta, ao_receber, ao_mudar_conexao=None, ao_erro=None, intervalo_reconexao_s=1.0):
        self.host, self.porta = host, porta
        self.ao_receber = ao_receber
        self.ao_mudar_conexao = ao_mudar_conexao or (lambda conectado: None)
        self.ao_erro = ao_erro or (lambda texto: None)
        self.intervalo_reconexao_s = intervalo_reconexao_s
        self._socket = None
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._laco, name='cliente_socket_ponte', daemon=True)

    @property
    def conectado(self):
        return self._socket is not None

    def iniciar(self):
        self._thread.start()

    def parar(self):
        self._parar.set()
        self._fechar()
        self._thread.join(timeout=2.0)

    def enviar(self, mensagem):
        """Envia uma mensagem; devolve False se não houver conexão."""
        dados = codificar(mensagem)
        with self._trava:
            if self._socket is None:
                return False
            try:
                self._socket.sendall(dados)
                return True
            except OSError as erro:
                self.ao_erro(f'falha ao enviar: {erro}')
        self._fechar()
        return False

    def _fechar(self):
        with self._trava:
            sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
            self.ao_mudar_conexao(False)

    def _laco(self):
        while not self._parar.is_set():
            try:
                sock = socket.create_connection((self.host, self.porta), timeout=2.0)
            except OSError:
                self._parar.wait(self.intervalo_reconexao_s)
                continue
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(0.5)
            with self._trava:
                self._socket = sock
            self.ao_mudar_conexao(True)
            leitor = LeitorLinhas()
            while not self._parar.is_set() and self._socket is sock:
                try:
                    dados = sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not dados:
                    break
                try:
                    for linha in leitor.alimentar(dados):
                        try:
                            self.ao_receber(decodificar(linha))
                        except ErroProtocolo as erro:
                            self.ao_erro(str(erro))
                except ErroProtocolo as erro:
                    self.ao_erro(str(erro))
            self._fechar()
            if not self._parar.is_set():
                time.sleep(self.intervalo_reconexao_s)
