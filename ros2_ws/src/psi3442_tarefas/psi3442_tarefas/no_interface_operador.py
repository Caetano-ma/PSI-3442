"""ParserComandos (nível n) e nó ROS 2 da interface do operador (R03).

Aceita só "executar tarefa 1", "executar tarefa 2" e "interromper" (maiúsculas, acentos e espaços extras são
ignorados). Não há pilotagem. Publica /operador/comando; assina /tarefa/status e /falhas e mostra no terminal a
resposta do gerenciador e as falhas.

Uso interativo:   ros2 run psi3442_tarefas interface_operador
Comando único:    ros2 run psi3442_tarefas interface_operador --comando "executar tarefa 1"
"""
import unicodedata

from .tipos import EXECUTAR_TAREFA1, EXECUTAR_TAREFA2, INTERROMPER

COMANDOS = {
    'executar tarefa 1': EXECUTAR_TAREFA1,
    'executar tarefa 2': EXECUTAR_TAREFA2,
    'interromper': INTERROMPER,
}


def normalizar(texto):
    sem_acentos = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return ' '.join(sem_acentos.lower().split())


def interpretar(texto):
    """Devolve a ação (EXECUTAR_TAREFA1, EXECUTAR_TAREFA2, INTERROMPER) ou None se o texto não for um comando."""
    return COMANDOS.get(normalizar(texto))


AJUDA = 'comandos: "executar tarefa 1", "executar tarefa 2", "interromper", "sair"'


def main(args=None):
    import argparse
    import sys
    import threading

    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import ComandoOperador, Falha as FalhaMsg, StatusTarefa

    from . import ros_util
    from .tipos import NOMES_REACAO

    parser = argparse.ArgumentParser(description='Interface do operador (PSI3442).')
    parser.add_argument('--comando', help='envia um único comando e sai')
    opcoes, _ = parser.parse_known_args(sys.argv[1:] if args is None else args)

    class NoInterfaceOperador(Node):
        def __init__(self):
            super().__init__('interface_operador')
            self.pub = self.create_publisher(ComandoOperador, '/operador/comando', ros_util.QOS_CONFIAVEL)
            self.create_subscription(StatusTarefa, '/tarefa/status', self.ao_status, ros_util.QOS_CONFIAVEL)
            self.create_subscription(FalhaMsg, '/falhas', self.ao_falha, ros_util.QOS_CONFIAVEL)
            self.ultima = ('', '', '')

        def enviar(self, acao):
            self.pub.publish(ros_util.carimbar(self, ComandoOperador(acao=acao)))

        def ao_status(self, msg):
            chave = (msg.modo, msg.estado, msg.mensagem)
            if chave != self.ultima:
                self.ultima = chave
                vertice = f' {msg.nome_vertice}' if msg.nome_vertice else ''
                print(f'\n[{msg.modo}] {msg.estado}{vertice} — {msg.mensagem}', flush=True)

        def ao_falha(self, msg):
            print(f'\n[FALHA] {msg.nome_tipo} ({NOMES_REACAO.get(msg.reacao, msg.reacao)}): {msg.detalhe}',
                  flush=True)

    from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor

    rclpy.init(args=None)
    no = NoInterfaceOperador()
    executor = SingleThreadedExecutor()
    executor.add_node(no)

    def girar_executor():
        try:
            executor.spin()
        except (ExternalShutdownException, KeyboardInterrupt):
            pass

    girar = threading.Thread(target=girar_executor, daemon=True)
    girar.start()
    try:
        if opcoes.comando:
            acao = interpretar(opcoes.comando)
            if acao is None:
                print(f'comando inválido: {opcoes.comando!r}. {AJUDA}')
                return
            import time
            # espera a descoberta do assinante antes de publicar (o comando é sob demanda)
            limite = time.monotonic() + 5.0
            while no.pub.get_subscription_count() == 0 and time.monotonic() < limite:
                time.sleep(0.1)
            no.enviar(acao)
            time.sleep(1.0)
            return
        print(AJUDA, flush=True)
        for linha in sys.stdin:
            texto = linha.strip()
            if not texto:
                continue
            if normalizar(texto) in ('sair', 'exit', 'quit'):
                break
            acao = interpretar(texto)
            if acao is None:
                print(f'comando inválido. {AJUDA}', flush=True)
            else:
                no.enviar(acao)
    except KeyboardInterrupt:
        pass
    finally:
        # encerra o executor antes de destruir o nó: evita abortar com a thread ainda dentro do rclpy
        executor.shutdown(timeout_sec=1.0)
        if rclpy.ok():
            rclpy.shutdown()
        girar.join(timeout=2.0)
        no.destroy_node()


if __name__ == '__main__':
    main()
