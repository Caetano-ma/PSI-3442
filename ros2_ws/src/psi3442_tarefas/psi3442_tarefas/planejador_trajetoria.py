"""PlanejadorTrajetoria (nível n): sequência de setpoints da Tarefa 1 (P02, P03).

[A, B, C, D, A] no sentido abcd ou [A, D, C, B, A] no sentido adcb. Os índices 0..3 são as permanências
(sem segunda espera em A); o índice 4 é o retorno a A.
"""
from .tipos import Setpoint

SEQUENCIAS = {'abcd': ('A', 'B', 'C', 'D', 'A'), 'adcb': ('A', 'D', 'C', 'B', 'A')}


class PlanejadorTrajetoria:
    ULTIMO_INDICE_PERMANENCIA = 3
    INDICE_RETORNO = 4

    def __init__(self, vertices, sentido='abcd'):
        if sentido not in SEQUENCIAS:
            raise ValueError(f'sentido inválido: {sentido}')
        self.nomes = SEQUENCIAS[sentido]
        self.pontos = tuple(tuple(vertices[nome]) for nome in self.nomes)

    def __len__(self):
        return len(self.pontos)

    def setpoint(self, indice):
        x, y, z = self.pontos[indice]
        return Setpoint(ativo=True, x_m=x, y_m=y, z_m=z, indice=indice, nome=self.nomes[indice])

    def segmentos(self):
        """Trajetória nominal como segmentos 3D: subida vertical em A e as quatro arestas."""
        ax, ay, az = self.pontos[0]
        segmentos = [((ax, ay, 0.0), (ax, ay, az))]
        segmentos += [(self.pontos[i], self.pontos[i + 1]) for i in range(len(self.pontos) - 1)]
        return segmentos
