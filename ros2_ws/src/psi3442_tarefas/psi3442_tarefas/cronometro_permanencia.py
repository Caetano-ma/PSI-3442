"""CronometroPermanencia (nível n): permanência contínua de P03/P05.

Relógio monotônico injetado (o chamador passa `agora`, em segundos). Conta enquanto o veredito é "dentro",
zera quando sai e conclui aos `duracao_alvo_s` contínuos. Registra início, interrupções e duração de cada
tentativa.
"""
from dataclasses import dataclass
from typing import Optional

INICIADA = 'iniciada'
INTERROMPIDA = 'interrompida'
CONCLUIDA = 'concluida'


@dataclass
class Tentativa:
    inicio_s: float
    fim_s: Optional[float] = None
    concluida: bool = False

    @property
    def duracao_s(self):
        return 0.0 if self.fim_s is None else self.fim_s - self.inicio_s


class CronometroPermanencia:
    def __init__(self, duracao_alvo_s=60.0):
        self.duracao_alvo_s = duracao_alvo_s
        self.zerar()

    def zerar(self):
        self.inicio_s = None
        self.concluida = False
        self.tentativas = []
        self._ultimo_s = None

    @property
    def contando(self):
        return self.inicio_s is not None and not self.concluida

    @property
    def interrupcoes(self):
        return sum(1 for t in self.tentativas if not t.concluida and t.fim_s is not None)

    def decorrido(self, agora):
        if self.concluida:
            return self.tentativas[-1].duracao_s
        return 0.0 if self.inicio_s is None else agora - self.inicio_s

    def atualizar(self, dentro, agora):
        """Atualiza com uma amostra; devolve INICIADA, INTERROMPIDA, CONCLUIDA ou None."""
        if self._ultimo_s is not None and agora < self._ultimo_s:
            raise ValueError('relógio não monotônico')
        self._ultimo_s = agora
        if self.concluida:
            return None
        if not dentro:
            if self.inicio_s is None:
                return None
            self.tentativas[-1].fim_s = agora
            self.inicio_s = None
            return INTERROMPIDA
        if self.inicio_s is None:
            self.inicio_s = agora
            self.tentativas.append(Tentativa(inicio_s=agora))
            return INICIADA
        if agora - self.inicio_s >= self.duracao_alvo_s:
            self.tentativas[-1].fim_s = agora
            self.tentativas[-1].concluida = True
            self.concluida = True
            return CONCLUIDA
        return None
