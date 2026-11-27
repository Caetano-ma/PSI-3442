"""SupervisorTarefa2 (Questão 2): varredura da sala, seleção de alvos, aproximação, permanência de 60 s a
0 < d <= 5 cm (R04), afastamento e próximo alvo, até concluir ou abortar (R03).

aguardando -> preparando -> decolando -> subindo -> [girando <-> deslocando] (varredura)
    alvo confirmado no mapa -> aproximando -> confirmando -> aproximacaoFinal -> permanecendo
        -> BALAO_DESTRUIDO -> afastando -> próximo alvo ou retoma a varredura
    varredura completa -> retornando -> pousando -> concluida;  falha/interrupção em voo -> pousoSeguro -> abortada

- Balão destruído (permanência concluída) fica no mapa mas é ignorado; descartados (não confirmados de perto) e
  inalcançáveis também. Só balões de cor-alvo confirmados são aproximados; os demais são evitados (R06).
- Rotas: replanejadas a cada passo se um balão recém-mapeado passa a bloquear o trecho restante (R06).
- Centro do alvo refinado no ponto de espera: média das detecções de perto (caixa inteira, < 1,5 m), cuja distância
  pelo diâmetro aparente é bem mais precisa que a do mapa (que acumula observações de longe) e não sofre a deriva
  acumulada da estimação de estado, pois é medida logo antes da aproximação final.
- Distância estimada d = |c - p_frente| - r_balão, com c = centro do balão refinado (visão) e p_frente = frente das
  hélices (pose estimada + raio do envelope na direção do nariz). A validação usa a distância verdadeira da
  simulação (avaliador), que NÃO entra aqui (R05).
- Confirmação durante a permanência: cor dominante no centro da imagem igual à do alvo (o balão ocupa a imagem),
  ou detecção do alvo na direção esperada; perdida por mais de `tempo_sem_confirmacao_s`, a contagem reinicia.

Assina /tarefa/ativa, /estado, /dji/telemetria, /mapa e /alvos; publica /setpoint e /tarefa/evento a 10 Hz.
"""
from collections import namedtuple
import math

from .cronometro_permanencia import CONCLUIDA, INICIADA, INTERROMPIDA, CronometroPermanencia
from .no_mapeamento_local import CONFIRMADO, DESLOCAMENTO_CAMERA, ponto_da_deteccao, posicao_camera
from .tipos import DECOLAR, HABILITAR_CONTROLE_VIRTUAL, POUSAR, Evento, Setpoint, normalizar_graus

EM_VOO = ('decolando', 'subindo', 'girando', 'deslocando', 'aproximando', 'confirmando', 'aproximacaoFinal',
          'permanecendo', 'afastando', 'retornando')
FINAIS = ('aguardando', 'concluida', 'abortada')
INATIVO = Setpoint(ativo=False)
REPETICAO_POUSO_S = 5.0
TOL_AZIMUTE_GRAUS = 12.0
TEMPO_MAX_FORA_S = 15.0           # na permanência, sem voltar à faixa por mais que isto: nova tentativa
TEMPO_REFINO_S = 1.0              # no ponto de espera: média das detecções de perto antes da aproximação final
DISTANCIA_REFINO_M = 1.5          # só detecções mais próximas que isto refinam o centro do alvo
ALFA_ANCORA = 0.5                 # filtro da reancoragem do centro pela medida de proximidade (por quadro)
SALTO_MAX_ANCORA_M = 0.40         # medida de perto mais longe que isto do centro atual é descartada
PontoBalao = namedtuple('PontoBalao', 'id cor x_m y_m z_m')


def problemas_preparacao(estado, tel, bateria_minima_pct):
    if tel is None:
        return ['sem telemetria']
    problemas = []
    if not tel.conectado:
        problemas.append('aeronave desconectada')
    if tel.bateria_pct < bateria_minima_pct:
        problemas.append(f'bateria {tel.bateria_pct:.0f} % < {bateria_minima_pct:.0f} %')
    if not tel.posicionamento_visual_ativo:
        problemas.append('posicionamento visual inativo')
    if tel.acao_perda_sinal != 'pousar':
        problemas.append(f'ação em perda de sinal = {tel.acao_perda_sinal} (exigido: pousar)')
    if not tel.controle_virtual_ativo:
        problemas.append('controle virtual não habilitado')
    if tel.em_voo or tel.motores_ligados:
        problemas.append('aeronave não está pousada com motores desligados')
    if estado is None or not estado.valido:
        problemas.append('estimativa de estado inválida')
    return problemas


def distancia_ponto_segmento(p, a, b):
    ab = [bb - aa for aa, bb in zip(a, b)]
    comprimento2 = sum(c * c for c in ab)
    t = 0.0 if comprimento2 == 0 else max(0.0, min(1.0, sum((pp - aa) * c for pp, aa, c in zip(p, a, ab))
                                                    / comprimento2))
    return math.dist(p, [aa + t * c for aa, c in zip(a, ab)])


def pontos_de_busca(cfg):
    """Grade de pontos de varredura (serpentina) dentro do volume, começando no ponto de decolagem."""
    margem = 0.3
    xs, ys = [], []
    n_x = max(1, int(math.floor((cfg.volume_x_max_m - cfg.volume_x_min_m - 2 * margem) / cfg.passo_busca_m)) + 1)
    n_y = max(1, int(math.floor((cfg.volume_y_max_m - cfg.volume_y_min_m - 2 * margem) / cfg.passo_busca_m)) + 1)
    for i in range(n_x):
        xs.append(cfg.volume_x_min_m + margem + (cfg.volume_x_max_m - cfg.volume_x_min_m - 2 * margem)
                  * (i / (n_x - 1) if n_x > 1 else 0.5))
    for j in range(n_y):
        ys.append(cfg.volume_y_min_m + margem + (cfg.volume_y_max_m - cfg.volume_y_min_m - 2 * margem)
                  * (j / (n_y - 1) if n_y > 1 else 0.5))
    pontos = [(0.0, 0.0)]
    for j, y in enumerate(ys):
        for x in (xs if j % 2 == 0 else list(reversed(xs))):
            if math.hypot(x, y) > cfg.passo_busca_m / 2:
                pontos.append((x, y))
    return pontos


class MaquinaTarefa2:
    NUMERO = 2

    def __init__(self, cfg, bateria_minima_pct):
        """`cfg`: ConfigTarefa2."""
        self.cfg = cfg
        self.bateria_minima_pct = bateria_minima_pct
        self.cronometro = CronometroPermanencia(cfg.tempo_permanencia_s)
        self.pontos = pontos_de_busca(cfg)
        self.estado = 'aguardando'
        self.t_entrada = 0.0
        self._eventos = []
        self._ativa_anterior = 0
        self._reiniciar()

    def _reiniciar(self):
        self.indice_busca = 0
        self.direcoes = []
        self.destruidos, self.descartados, self.inalcancaveis = [], set(), set()
        self.tentativas = {}
        self.alvo = None
        self.rota = []                     # pontos intermediários até o destino atual
        self.d_estimada = math.nan
        self.vz_toque_mps = math.nan
        self._vz_em_voo = 0.0
        self._pouso_pedido_s = None
        self._parado_desde = None
        self._fora_desde = None
        self._ramp = None
        self._confirmado_s = None
        self._refino = []
        self._ancora = None
        self._t_medida = -math.inf        # última medida de proximidade do alvo (reancoragem)

    # ------------------------------------------------------------------ auxiliares
    def _rotulo(self):
        return f"{self.alvo['cor']}#{self.alvo['id']}" if self.alvo else ''

    def _evento(self, tipo, **campos):
        campos.setdefault('estado', self.estado)
        campos.setdefault('vertice', self.alvo['id'] if self.alvo else -1)
        campos.setdefault('nome_vertice', self._rotulo())
        self._eventos.append(Evento(tipo=tipo, tarefa=self.NUMERO, **campos))

    def _pedir(self, acao, agora, detalhe=''):
        self._evento('SOLICITA_ACAO', acao=acao, detalhe=detalhe)
        if acao == POUSAR:
            self._pouso_pedido_s = agora

    def _ir(self, novo, agora, detalhe=''):
        self.estado = novo
        self.t_entrada = agora
        self._parado_desde = None
        self._evento('TRANSICAO', detalhe=detalhe)
        if novo == 'preparando':
            self._pedir(HABILITAR_CONTROLE_VIRTUAL, agora)
        elif novo == 'decolando':
            self._pedir(DECOLAR, agora)
        elif novo == 'confirmando':
            self._refino, self._confirmado_s = [], None
        elif novo == 'permanecendo':
            self.cronometro.zerar()
            self._fora_desde = None
        elif novo == 'pousando':
            self._pouso_pedido_s = None
        elif novo == 'pousoSeguro':
            self._pedir(POUSAR, agora, 'pouso no local')
        elif novo == 'concluida':
            self._evento('TAREFA_CONCLUIDA', valor=self.vz_toque_mps, detalhe=self._resumo())
        elif novo == 'abortada':
            self._evento('TAREFA_ABORTADA', valor=self.vz_toque_mps, detalhe=detalhe or self._resumo())

    def _resumo(self):
        destruidos = ', '.join(f'{cor}#{i} ({d:.0f} s)' for i, cor, d in self.destruidos) or 'nenhum'
        return (f'balões destruídos: {destruidos}; descartados: {sorted(self.descartados) or "nenhum"}; '
                f'inalcançáveis: {sorted(self.inalcancaveis) or "nenhum"}; |vz| no toque = {self.vz_toque_mps:.2f} m/s')

    def _setpoint(self, x, y, z, guinada, nome):
        return Setpoint(ativo=True, x_m=x, y_m=y, z_m=z, indice=self.alvo['id'] if self.alvo else -1, nome=nome,
                        guinada_ativa=guinada is not None, guinada_graus=0.0 if guinada is None else guinada)

    def _chegou(self, estado, ponto, guinada=None, tol=None):
        if estado is None or not estado.valido:
            return False
        tol = self.cfg.tol_posicao_m if tol is None else tol
        if math.dist((estado.x_m, estado.y_m, estado.z_m), ponto) > tol:
            return False
        if guinada is not None and abs(normalizar_graus(guinada - estado.guinada_local_graus)) > self.cfg.tol_guinada_graus:
            return False
        return math.sqrt(estado.vx_mps ** 2 + estado.vy_mps ** 2 + estado.vz_mps ** 2) <= self.cfg.v_pairado_max_mps

    def _no_volume(self, p, margem=0.0):
        c = self.cfg
        return (c.volume_x_min_m + margem <= p[0] <= c.volume_x_max_m - margem
                and c.volume_y_min_m + margem <= p[1] <= c.volume_y_max_m - margem
                and c.volume_z_min_m <= p[2] <= c.volume_z_max_m)

    def _folga_balao(self, b):
        alvo_atual = self.alvo is not None and b.id == self.alvo['id']
        margem = 0.0 if alvo_atual else (self.cfg.margem_obstaculos_m if b.alvo else self.cfg.margem_nao_alvo_m)
        return self.cfg.raio_balao_m + self.cfg.raio_envelope_frontal_m + margem

    def _bloqueio(self, a, b, mapa, ignorar_id=None):
        """Primeiro balão que bloqueia o segmento a -> b (exceto `ignorar_id`), ou None."""
        piores = []
        for balao in (mapa.baloes if mapa is not None else []):
            if balao.id == ignorar_id:
                continue
            c = (balao.x_m, balao.y_m, balao.z_m)
            d = distancia_ponto_segmento(c, a, b)
            if d < self._folga_balao(balao):
                piores.append((d, balao))
        return min(piores, key=lambda par: par[0])[1] if piores else None

    def _obstaculo(self, mapa, p):
        return mapa is not None and hasattr(mapa, 'obstaculo_perto') and mapa.obstaculo_perto(
            p[0], p[1], self.cfg.margem_obstaculos_m)

    def _planejar_rota(self, origem, destino, mapa, ignorar_id=None):
        """Menor rota até `destino` num grafo de visibilidade: nós em 8 direções em volta de cada balão do mapa (à
        altura do destino), arestas só onde nenhum balão bloqueia o segmento (R06). None se não há rota livre.
        Se a aeronave já está dentro da folga de um balão, a primeira aresta pode sair dela."""
        baloes = [b for b in (mapa.baloes if mapa is not None else []) if b.id != ignorar_id]
        dentro = {b.id for b in baloes if math.dist((b.x_m, b.y_m, b.z_m), origem) < self._folga_balao(b)}
        nos = [tuple(origem), tuple(destino)]
        for b in baloes:
            raio = self._folga_balao(b) + 0.15
            for k in range(8):
                a = math.radians(45 * k + 22.5)
                p = (b.x_m + raio * math.cos(a), b.y_m + raio * math.sin(a), destino[2])
                if (self._no_volume(p) and not self._obstaculo(mapa, p) and not any(
                        math.dist((o.x_m, o.y_m, o.z_m), p) < self._folga_balao(o) for o in baloes)):
                    nos.append(p)

        def livre(i, j):
            for b in baloes:
                if i == 0 and b.id in dentro:
                    continue
                if distancia_ponto_segmento((b.x_m, b.y_m, b.z_m), nos[i], nos[j]) < self._folga_balao(b):
                    return False
            return True

        custo, anterior, abertos = {0: 0.0}, {}, set(range(len(nos)))
        while abertos:
            i = min((k for k in abertos if k in custo), key=custo.get, default=None)
            if i is None:
                return None
            if i == 1:
                break
            abertos.discard(i)
            for j in abertos:
                c = custo[i] + math.dist(nos[i], nos[j])
                if c < custo.get(j, math.inf) and livre(i, j):
                    custo[j], anterior[j] = c, i
        else:
            return None
        rota, k = [], 1
        while k != 0:
            rota.append(nos[k])
            k = anterior[k]
        return rota[::-1]

    def _rota_bloqueada(self, estado, mapa, ignorar_id=None):
        if estado is None or not estado.valido or not self.rota:
            return False
        pontos = [(estado.x_m, estado.y_m, estado.z_m)] + list(self.rota)
        for k, (a, b) in enumerate(zip(pontos, pontos[1:])):
            bloqueio = self._bloqueio(a, b, mapa, ignorar_id)
            if bloqueio is not None and not (k == 0 and math.dist(
                    (bloqueio.x_m, bloqueio.y_m, bloqueio.z_m), a) < self._folga_balao(bloqueio)):
                return True
        return False

    def _replanejar(self, estado, mapa, ignorar_id=None):
        """Refaz a rota até o destino atual se um balão passou a bloqueá-la; False se não há rota livre."""
        if not self._rota_bloqueada(estado, mapa, ignorar_id):
            return True
        rota = self._planejar_rota((estado.x_m, estado.y_m, estado.z_m), self.rota[-1], mapa, ignorar_id)
        if rota is None:
            return False
        self.rota = rota
        return True

    def _destino_livre(self, destino, mapa):
        return not self._obstaculo(mapa, destino) and not any(
            math.dist((b.x_m, b.y_m, b.z_m), destino) < self._folga_balao(b) for b in (mapa.baloes if mapa else []))

    def distancia_estimada(self, estado, centro):
        g = math.radians(estado.guinada_local_graus)
        r = self.cfg.raio_envelope_frontal_m
        frente = (estado.x_m + r * math.cos(g), estado.y_m + r * math.sin(g), estado.z_m)
        return math.dist(frente, centro) - self.cfg.raio_balao_m

    # ------------------------------------------------------------------ escolha e aproximação
    def _escolher_alvo(self, mapa, estado):
        ignorar = {i for i, _, _ in self.destruidos} | self.descartados | self.inalcancaveis
        opcoes = [b for b in (mapa.baloes if mapa is not None else [])
                  if b.alvo and b.situacao == CONFIRMADO and b.id not in ignorar]
        if not opcoes or estado is None or not estado.valido:
            return None
        return min(opcoes, key=lambda b: math.dist((b.x_m, b.y_m, b.z_m), (estado.x_m, estado.y_m, estado.z_m)))

    def _geometria_aproximacao(self, balao, estado, mapa):
        """Ponto de espera, ponto final e guinada; testa 8 direções em volta do balão (R06)."""
        c = self.cfg
        centro = (balao.x_m, balao.y_m, balao.z_m)
        z = min(max(balao.z_m, c.volume_z_min_m), c.volume_z_max_m)
        dx, dy = estado.x_m - balao.x_m, estado.y_m - balao.y_m
        base = math.atan2(dy, dx) if math.hypot(dx, dy) > 1e-6 else math.pi
        for delta in (0, 45, -45, 90, -90, 135, -135, 180):
            ang = base + math.radians(delta)
            u = (math.cos(ang), math.sin(ang))
            raio = c.raio_balao_m + c.raio_envelope_frontal_m
            espera = (balao.x_m + u[0] * (raio + c.distancia_aproximacao_m),
                      balao.y_m + u[1] * (raio + c.distancia_aproximacao_m), z)
            final = (balao.x_m + u[0] * (raio + c.d_alvo_m), balao.y_m + u[1] * (raio + c.d_alvo_m), z)
            if not (self._no_volume(espera) and self._no_volume(final)):
                continue
            if self._obstaculo(mapa, espera) or self._obstaculo(mapa, final):
                continue
            if self._bloqueio(espera, final, mapa, ignorar_id=balao.id) is not None:
                continue
            guinada = math.degrees(math.atan2(-u[1], -u[0]))
            return {'id': balao.id, 'cor': balao.cor, 'centro': centro, 'espera': espera, 'final': final,
                    'guinada': guinada, 'direcao': u}
        return None

    def _iniciar_aproximacao(self, balao, agora, estado, mapa):
        geo = self._geometria_aproximacao(balao, estado, mapa)
        if geo is None:
            self.inalcancaveis.add(balao.id)
            self.alvo = {'id': balao.id, 'cor': balao.cor}
            self._evento('ALVO_INALCANCAVEL', detalhe='sem ponto de aproximação livre no volume permitido')
            self.alvo = None
            return False
        origem = (estado.x_m, estado.y_m, estado.z_m)
        rota = self._planejar_rota(origem, geo['espera'], mapa, ignorar_id=balao.id)
        if rota is None:
            self.inalcancaveis.add(balao.id)
            self.alvo = geo
            self._evento('ALVO_INALCANCAVEL', detalhe='caminho bloqueado')
            self.alvo = None
            return False
        self.alvo, self.rota = geo, rota
        self.tentativas.setdefault(balao.id, 0)
        self._evento('ALVO_SELECIONADO', detalhe=f'centro estimado ({balao.x_m:.2f}, {balao.y_m:.2f}, '
                                                 f'{balao.z_m:.2f}) m, incerteza {balao.incerteza_m:.2f} m')
        self._ir('aproximando', agora, 'alvo confirmado no mapa')
        return True

    def _atualizar_centro(self, mapa):
        for b in (mapa.baloes if mapa is not None else []):
            if self.alvo is not None and b.id == self.alvo['id']:
                self.alvo['centro'] = (b.x_m, b.y_m, b.z_m)

    def _decidir(self, agora, estado, mapa, detalhe=''):
        balao = self._escolher_alvo(mapa, estado)
        if balao is not None and self._iniciar_aproximacao(balao, agora, estado, mapa):
            return
        self.alvo = None
        if self.direcoes:
            self._ir('girando', agora, detalhe or 'retoma a varredura')
        elif self.indice_busca + 1 < len(self.pontos):
            self._proximo_ponto(agora, estado, mapa)
        else:
            self._ir('retornando', agora, detalhe or 'varredura completa')

    def _proximo_ponto(self, agora, estado, mapa):
        while self.indice_busca + 1 < len(self.pontos):
            self.indice_busca += 1
            x, y = self.pontos[self.indice_busca]
            destino = (x, y, self.cfg.altura_busca_m)
            origem = (estado.x_m, estado.y_m, estado.z_m) if estado is not None else destino
            rota = self._planejar_rota(origem, destino, mapa)
            if rota is not None and self._destino_livre(destino, mapa):
                self.rota = rota
                self._ir('deslocando', agora, f'ponto de busca {self.indice_busca}')
                return
        self._ir('retornando', agora, 'varredura completa')

    def _comecar_giro(self, estado):
        g0 = estado.guinada_local_graus if estado is not None else 0.0
        passos = int(round(360.0 / self.cfg.passo_giro_graus))
        self.direcoes = [normalizar_graus(g0 + k * self.cfg.passo_giro_graus) for k in range(1, passos + 1)]

    def _confirmacao_visual(self, visao, agora, guinada_esperada):
        if visao is None or agora - visao.t > self.cfg.tempo_sem_confirmacao_s:
            return False
        cor = self.alvo['cor']
        if visao.cor_central == cor and visao.fracao_cor_central >= self.cfg.fracao_cor_central_min:
            return True
        return any(d.cor == cor and abs(normalizar_graus(d.azimute_graus - guinada_esperada)) <= TOL_AZIMUTE_GRAUS
                   for d in visao.deteccoes)

    # ------------------------------------------------------------------ passo (10 Hz)
    def passo(self, agora, ativa, estado, tel, mapa=None, visao=None):
        """`mapa`: mapa local (baloes, obstaculo_perto opcional); `visao`: último /alvos (t, deteccoes, cor_central,
        fracao_cor_central). Devolve (setpoint, eventos)."""
        self._eventos = []
        ativada = ativa == self.NUMERO and self._ativa_anterior != self.NUMERO
        desativada = ativa != self.NUMERO and self._ativa_anterior == self.NUMERO
        self._ativa_anterior = ativa
        if tel is not None and tel.em_voo and estado is not None and estado.valido:
            self._vz_em_voo = estado.vz_mps

        if self.estado in FINAIS:
            if ativada:
                self._reiniciar()
                self._ir('preparando', agora)
            return INATIVO, self._eventos
        if desativada:
            if self.estado == 'preparando':
                self._ir('aguardando', agora, 'interrompida na preparação')
                self._evento('TAREFA_ABORTADA', detalhe='interrompida na preparação')
                return INATIVO, self._eventos
            if self.estado in EM_VOO or self.estado == 'pousando':
                self._ir('pousoSeguro', agora, 'interrupção (operador ou falha)')
        setpoint = getattr(self, '_em_' + self.estado)(agora, estado, tel, mapa, visao)
        return setpoint, self._eventos

    # ------------------------------------------------------------------ estados
    def _em_preparando(self, agora, estado, tel, mapa, visao):
        problemas = problemas_preparacao(estado, tel, self.bateria_minima_pct)
        if not problemas:
            self._ir('decolando', agora, 'PreparacaoConcluida')
        elif agora - self.t_entrada > self.cfg.tempo_max_preparacao_s:
            self._evento('PREPARACAO_FALHOU', detalhe='; '.join(problemas))
            self._ir('aguardando', agora, 'FalhaDetectada na preparação')
        return INATIVO

    def _em_decolando(self, agora, estado, tel, mapa, visao):
        if (tel is not None and tel.em_voo and estado is not None and estado.valido
                and estado.z_m >= self.cfg.altura_min_decolagem_m and abs(estado.vz_mps) <= self.cfg.v_pairado_max_mps):
            self._ir('subindo', agora, 'DecolagemConcluida')
        elif agora - self.t_entrada > self.cfg.tempo_max_decolagem_s:
            self._ir('pousoSeguro', agora, 'decolagem não concluída no prazo')
        return INATIVO

    def _em_subindo(self, agora, estado, tel, mapa, visao):
        destino = (0.0, 0.0, self.cfg.altura_busca_m)
        if self._chegou(estado, destino):
            self._comecar_giro(estado)
            self._ir('girando', agora, 'altura de busca atingida')
        return self._setpoint(*destino, None, 'subida')

    def _em_girando(self, agora, estado, tel, mapa, visao):
        balao = self._escolher_alvo(mapa, estado)
        if balao is not None and self._iniciar_aproximacao(balao, agora, estado, mapa):
            return self._em_aproximando(agora, estado, tel, mapa, visao)
        x, y = self.pontos[self.indice_busca]
        ponto = (x, y, self.cfg.altura_busca_m)
        if not self.direcoes:
            self._decidir(agora, estado, mapa)
            return self._setpoint(*ponto, None, 'busca')
        guinada = self.direcoes[0]
        if self._chegou(estado, ponto, guinada, tol=0.3):
            if self._parado_desde is None:
                self._parado_desde = agora
            elif agora - self._parado_desde >= self.cfg.pausa_giro_s:
                self.direcoes.pop(0)
                self._parado_desde = None
        else:
            self._parado_desde = None
        return self._setpoint(*ponto, guinada, f'busca {self.indice_busca}')

    def _seguir_rota(self, estado, guinada_final=None, tol=None):
        """Avança pelos pontos da rota; devolve (ponto atual, guinada, chegou ao fim)."""
        while len(self.rota) > 1 and self._chegou(estado, self.rota[0], tol=0.3):
            self.rota.pop(0)
        alvo = self.rota[0]
        ultimo = len(self.rota) == 1
        if ultimo and guinada_final is not None:
            guinada = guinada_final
        elif estado is not None and math.hypot(alvo[0] - estado.x_m, alvo[1] - estado.y_m) > 0.3:
            guinada = math.degrees(math.atan2(alvo[1] - estado.y_m, alvo[0] - estado.x_m))
        else:
            guinada = guinada_final
        return alvo, guinada, ultimo and self._chegou(estado, alvo, guinada, tol)

    def _em_deslocando(self, agora, estado, tel, mapa, visao):
        balao = self._escolher_alvo(mapa, estado)
        if balao is not None and self._iniciar_aproximacao(balao, agora, estado, mapa):
            return self._em_aproximando(agora, estado, tel, mapa, visao)
        if not self._replanejar(estado, mapa) or not self._destino_livre(self.rota[-1], mapa):
            self._proximo_ponto(agora, estado, mapa)
            return self._setpoint(estado.x_m, estado.y_m, estado.z_m, None, 'replanejando')
        ponto, guinada, chegou = self._seguir_rota(estado, tol=0.3)
        if chegou:
            self._comecar_giro(estado)
            self._ir('girando', agora, f'ponto de busca {self.indice_busca} atingido')
        return self._setpoint(*ponto, guinada, f'busca {self.indice_busca}')

    def _em_aproximando(self, agora, estado, tel, mapa, visao):
        if not self._replanejar(estado, mapa, self.alvo['id']):
            self.inalcancaveis.add(self.alvo['id'])
            self._evento('ALVO_INALCANCAVEL', detalhe='caminho bloqueado por balão mapeado no trajeto')
            self._decidir(agora, estado, mapa)
            return self._setpoint(estado.x_m, estado.y_m, estado.z_m, None, 'replanejando')
        ponto, guinada, chegou = self._seguir_rota(estado, self.alvo['guinada'])
        if chegou:
            self._ir('confirmando', agora, 'ponto de espera atingido')
        return self._setpoint(*ponto, guinada, f'espera {self._rotulo()}')

    def _em_confirmando(self, agora, estado, tel, mapa, visao):
        espera, guinada = self.alvo['espera'], self.alvo['guinada']
        if self._confirmacao_visual(visao, agora, guinada):
            if self._confirmado_s is None:
                self._confirmado_s = agora
            self._acumular_refino(visao, guinada)
        if self._confirmado_s is not None and agora - self._confirmado_s >= TEMPO_REFINO_S:
            self._atualizar_centro(mapa)
            if len(self._refino) >= 3:
                pontos = [p for _, p in self._refino]
                self.alvo['centro'] = tuple(sum(c) / len(pontos) for c in zip(*pontos))
            geo = self._geometria_aproximacao(PontoBalao(self.alvo['id'], self.alvo['cor'], *self.alvo['centro']),
                                              estado, mapa)
            if geo is not None and math.dist(geo['espera'], espera) < 0.5:
                self.alvo.update(final=geo['final'], centro=geo['centro'], direcao=geo['direcao'])
            self._ramp = espera
            self._ir('aproximacaoFinal', agora, f'alvo confirmado de perto ({len(self._refino)} medidas); centro '
                                                '({:.2f}, {:.2f}, {:.2f}) m'.format(*self.alvo['centro']))
        elif self._confirmado_s is None and agora - self.t_entrada > self.cfg.tempo_confirmacao_s:
            self.descartados.add(self.alvo['id'])
            self._evento('ALVO_DESCARTADO', detalhe='não confirmado pela visão no ponto de espera')
            self._decidir(agora, estado, mapa)
            return self._setpoint(*espera, guinada, 'descartado')
        return self._setpoint(*espera, guinada, f'confirmação {self._rotulo()}')

    def _acumular_refino(self, visao, guinada):
        """Guarda o ponto de cada detecção de perto do alvo (uma por quadro de visão)."""
        if visao is None or (self._refino and self._refino[-1][0] is visao):
            return
        dets = [d for d in visao.deteccoes if d.cor == self.alvo['cor'] and not d.cortada
                and 0 < d.distancia_m < DISTANCIA_REFINO_M
                and abs(normalizar_graus(d.azimute_graus - guinada)) <= TOL_AZIMUTE_GRAUS]
        if dets:
            d = min(dets, key=lambda d: abs(normalizar_graus(d.azimute_graus - guinada)))
            p = ponto_da_deteccao(visao.x_m, visao.y_m, visao.z_m, visao.guinada_local_graus, d)
            if math.dist(p, self.alvo['centro']) < 0.5:
                self._refino.append((visao, p))

    def _medida_proxima(self, visao, agora):
        """Centro do alvo medido neste quadro, no referencial estimado: pela proximidade (bordas na linha central) ou,
        sem ela, pela detecção de perto (caixa inteira) mais próxima do centro atual. None se não há medida."""
        if visao is None or agora - visao.t > self.cfg.tempo_sem_confirmacao_s:
            return None
        centro = self.alvo['centro']
        d, az = getattr(visao, 'distancia_central_m', math.nan), getattr(visao, 'azimute_central_graus', math.nan)
        if visao.cor_central == self.alvo['cor'] and math.isfinite(d) and (d < 0 or math.isfinite(az)) \
                and d < DISTANCIA_REFINO_M:
            cx, cy, cz = posicao_camera(visao.x_m, visao.y_m, visao.z_m, visao.guinada_local_graus)
            if d < 0:
                # balão cortado pela borda da imagem: só se sabe que a distância é no máximo |d|. Restrição de um
                # lado só: corrige o centro apenas se a previsão está mais longe que isso (afasta a aeronave)
                previsto = math.dist((cx, cy, cz), centro)
                # o limite só vale para a contagem se ele mesmo garante d <= d_max (câmera atrás da frente)
                if -d - self.cfg.raio_balao_m - (self.cfg.raio_envelope_frontal_m - DESLOCAMENTO_CAMERA[0]) \
                        <= self.cfg.d_max_m:
                    self._t_medida = agora
                if previsto <= -d:
                    return None
                return tuple(c + (p - c) * (-d) / previsto for c, p in zip((cx, cy, cz), centro))
            h = math.sqrt(max(d * d - (centro[2] - cz) ** 2, 0.0))
            self._t_medida = agora
            return cx + h * math.cos(math.radians(az)), cy + h * math.sin(math.radians(az)), centro[2]
        pontos = [ponto_da_deteccao(visao.x_m, visao.y_m, visao.z_m, visao.guinada_local_graus, det)
                  for det in visao.deteccoes if det.cor == self.alvo['cor'] and not det.cortada
                  and 0 < det.distancia_m < DISTANCIA_REFINO_M]
        return min(pontos, key=lambda p: math.dist(p, centro)) if pontos else None

    def _reancorar(self, visao, agora):
        """Reposiciona o centro do alvo no referencial estimado pela medida de perto e, com ele, os pontos de espera
        e final. Assim a aproximação e a permanência seguem o balão, e não a posição integrada, que deriva (R04)."""
        if visao is None or self._ancora is visao:
            return
        self._ancora = visao
        medido = self._medida_proxima(visao, agora)
        if medido is None or math.dist(medido, self.alvo['centro']) > SALTO_MAX_ANCORA_M:
            return
        centro = tuple((1 - ALFA_ANCORA) * c + ALFA_ANCORA * m for c, m in zip(self.alvo['centro'], medido))
        u, c = self.alvo['direcao'], self.cfg
        raio = c.raio_balao_m + c.raio_envelope_frontal_m
        self.alvo['centro'] = centro
        self.alvo['final'] = (centro[0] + u[0] * (raio + c.d_alvo_m), centro[1] + u[1] * (raio + c.d_alvo_m),
                              self.alvo['final'][2])
        self.alvo['espera'] = (centro[0] + u[0] * (raio + c.distancia_aproximacao_m),
                               centro[1] + u[1] * (raio + c.distancia_aproximacao_m), self.alvo['espera'][2])

    def _em_aproximacaoFinal(self, agora, estado, tel, mapa, visao):
        self._reancorar(visao, agora)
        final, guinada = self.alvo['final'], self.alvo['guinada']
        passo = self.cfg.v_aproximacao_final_mps * 0.1
        restante = math.dist(self._ramp, final)
        if restante <= passo:
            self._ramp = final
        else:
            self._ramp = tuple(r + (f - r) * passo / restante for r, f in zip(self._ramp, final))
        if estado is not None and estado.valido:
            self.d_estimada = self.distancia_estimada(estado, self.alvo['centro'])
            if self._ramp == final and 0 < self.d_estimada <= self.cfg.d_max_m:
                self._ir('permanecendo', agora, f'faixa atingida: d = {self.d_estimada * 100:.1f} cm')
        return self._setpoint(*self._ramp, guinada, f'aproximação {self._rotulo()}')

    def _em_permanecendo(self, agora, estado, tel, mapa, visao):
        self._reancorar(visao, agora)
        final, guinada = self.alvo['final'], self.alvo['guinada']
        setpoint = self._setpoint(*final, guinada, f'permanência {self._rotulo()}')
        if estado is None or not estado.valido:
            dentro = False
        else:
            self.d_estimada = self.distancia_estimada(estado, self.alvo['centro'])
            velocidade = math.sqrt(estado.vx_mps ** 2 + estado.vy_mps ** 2 + estado.vz_mps ** 2)
            # contagem só com medida direta recente: sem ela, a distância é só a posição integrada, que deriva
            confirmado = (self._confirmacao_visual(visao, agora, guinada)
                          and agora - self._t_medida <= self.cfg.tempo_sem_confirmacao_s)
            dentro = (0 < self.d_estimada <= self.cfg.d_max_m and confirmado
                      and velocidade <= self.cfg.v_pairado_max_mps)
            if self.d_estimada <= 0:
                self._evento('COLISAO_ESTIMADA', valor=self.d_estimada,
                             detalhe=f'd estimada = {self.d_estimada * 100:.1f} cm: afastando')
                return self._nova_tentativa(agora, estado, mapa, 'contato estimado')
        resultado = self.cronometro.atualizar(dentro, agora)
        d_cm = self.d_estimada * 100 if math.isfinite(self.d_estimada) else float('nan')
        if resultado == INICIADA:
            self._evento('PERMANENCIA_INICIADA', valor=self.d_estimada, detalhe=f'd = {d_cm:.1f} cm')
        elif resultado == INTERROMPIDA:
            self._evento('PERMANENCIA_INTERROMPIDA', permanencia_s=self.cronometro.tentativas[-1].duracao_s,
                         valor=self.d_estimada, detalhe=f'saiu da faixa ou perdeu a confirmação: d = {d_cm:.1f} cm')
        elif resultado == CONCLUIDA:
            duracao = self.cronometro.tentativas[-1].duracao_s
            self._evento('PERMANENCIA_CONCLUIDA', permanencia_s=duracao, valor=self.d_estimada,
                         detalhe=f'{self.cronometro.interrupcoes} reinícios da contagem')
            self.destruidos.append((self.alvo['id'], self.alvo['cor'], duracao))
            self._evento('BALAO_DESTRUIDO', valor=float(self.alvo['id']), x_m=self.alvo['centro'][0],
                         y_m=self.alvo['centro'][1], z_m=self.alvo['centro'][2],
                         detalhe=f"{self.alvo['cor']} #{self.alvo['id']}: {duracao:.1f} s contínuos a "
                                 f"0 < d <= {self.cfg.d_max_m * 100:.0f} cm")
            self.rota = [self.alvo['espera']]
            self._ir('afastando', agora, 'BalaoDestruido')
            return self._setpoint(*self.alvo['espera'], guinada, f'afastando {self._rotulo()}')
        if dentro or self.cronometro.contando:
            self._fora_desde = None
        elif self._fora_desde is None:
            self._fora_desde = agora
        elif agora - self._fora_desde > TEMPO_MAX_FORA_S:
            return self._nova_tentativa(agora, estado, mapa, 'sem voltar à faixa')
        return setpoint

    def _nova_tentativa(self, agora, estado, mapa, motivo):
        id_alvo = self.alvo['id']
        self.tentativas[id_alvo] = self.tentativas.get(id_alvo, 0) + 1
        self.rota = [self.alvo['espera']]
        self._ir('afastando', agora, f'{motivo}: tentativa {self.tentativas[id_alvo]} de '
                                     f'{self.cfg.tentativas_por_balao}')
        return self._setpoint(*self.alvo['espera'], self.alvo['guinada'], f'afastando {self._rotulo()}')

    def _em_afastando(self, agora, estado, tel, mapa, visao):
        ponto, guinada, chegou = self._seguir_rota(estado, self.alvo['guinada'])
        if chegou:
            id_alvo = self.alvo['id']
            destruido = any(i == id_alvo for i, _, _ in self.destruidos)
            if not destruido and self.tentativas.get(id_alvo, 0) < self.cfg.tentativas_por_balao:
                self._ramp = self.alvo['espera']
                self._ir('confirmando', agora, 'nova tentativa')
            else:
                if not destruido:
                    self.inalcancaveis.add(id_alvo)
                    self._evento('ALVO_INALCANCAVEL', detalhe='tentativas esgotadas')
                self._decidir(agora, estado, mapa)
        return self._setpoint(*ponto, guinada, f'afastando {self._rotulo()}')

    def _em_retornando(self, agora, estado, tel, mapa, visao):
        destino = (0.0, 0.0, self.cfg.altura_busca_m)
        if not self.rota or self.rota[-1] != destino:
            origem = (estado.x_m, estado.y_m, estado.z_m) if estado is not None else destino
            self.rota = self._planejar_rota(origem, destino, mapa) or [destino]
        elif not self._replanejar(estado, mapa):
            self.rota = [destino]
        ponto, guinada, chegou = self._seguir_rota(estado, 0.0)
        if chegou:
            self._ir('pousando', agora, 'ponto de decolagem atingido')
        return self._setpoint(*ponto, guinada, 'retorno')

    def _pousado(self, tel):
        return tel is not None and not tel.em_voo and not tel.motores_ligados

    def _em_pousando(self, agora, estado, tel, mapa, visao):
        if self._pousado(tel):
            return self._confirmar_pouso(agora, 'concluida')
        if self._pouso_pedido_s is None:
            altura = self.cfg.altura_inicio_pouso_m
            if estado is not None and estado.valido and estado.z_m <= altura + 0.1:
                self._pedir(POUSAR, agora, 'pouso automático a partir de %.2f m' % estado.z_m)
                return INATIVO
            return self._setpoint(0.0, 0.0, altura, 0.0, 'pouso')
        if agora - self._pouso_pedido_s > REPETICAO_POUSO_S:
            self._pedir(POUSAR, agora, 'pouso ainda não confirmado: pedido repetido')
        return INATIVO

    def _em_pousoSeguro(self, agora, estado, tel, mapa, visao):
        if self._pousado(tel):
            return self._confirmar_pouso(agora, 'abortada')
        if self._pouso_pedido_s is None or agora - self._pouso_pedido_s > REPETICAO_POUSO_S:
            self._pedir(POUSAR, agora, 'pouso ainda não confirmado: pedido repetido')
        return INATIVO

    def _confirmar_pouso(self, agora, destino):
        self.vz_toque_mps = abs(self._vz_em_voo)
        self._evento('POUSO_CONFIRMADO', valor=self.vz_toque_mps, detalhe=f'|vz| no toque = {self.vz_toque_mps:.2f} m/s')
        self._ir(destino, agora, 'PousoConfirmado')
        return INATIVO


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from psi3442_interfaces.msg import Alvos, EstadoEstimado, EventoTarefa, MapaLocal, Setpoint as SetpointMsg
    from psi3442_interfaces.msg import TarefaAtiva, Telemetria as TelemetriaMsg

    from . import ros_util
    from .tipos import Estado, Telemetria, copiar_campos, de_mensagem

    class MapaRecebido:
        """Adapta MapaLocal (mensagem) ao que a máquina usa: baloes e obstaculo_perto."""

        def __init__(self, msg):
            self.baloes = msg.baloes
            self.msg = msg

        def obstaculo_perto(self, x, y, margem):
            m = self.msg
            r = m.resolucao_m
            n = int(math.ceil(margem / r))
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    if math.hypot(i * r, j * r) > margem:
                        continue
                    ci = int((x + i * r - m.origem_x_m) / r)
                    cj = int((y + j * r - m.origem_y_m) / r)
                    if 0 <= ci < m.largura and 0 <= cj < m.altura and m.ocupacao[cj * m.largura + ci] == 100:
                        return True
            return False

    class VisaoRecebida:
        def __init__(self, msg, t):
            self.msg, self.t = msg, t

        def __getattr__(self, nome):
            return getattr(self.msg, nome)

    class NoTarefa2(Node):
        def __init__(self):
            super().__init__('tarefa2')
            cfg = ros_util.carregar_config(self)
            self.prazo_telemetria_s = cfg.seguranca.prazo_telemetria_s
            self.prazo_estado_s = cfg.estimacao.idade_max_amostra_s
            self.maquina = MaquinaTarefa2(cfg.tarefa2, cfg.seguranca.bateria_minima_pct)
            self.ativa = 0
            self.estado, self.t_estado = None, None
            self.tel, self.t_tel = None, None
            self.mapa, self.visao = None, None
            self.pub_setpoint = self.create_publisher(SetpointMsg, '/setpoint', ros_util.QOS_FLUXO)
            self.pub_evento = self.create_publisher(EventoTarefa, '/tarefa/evento', ros_util.QOS_CONFIAVEL)
            self.create_subscription(TarefaAtiva, '/tarefa/ativa', self.ao_ativa, ros_util.QOS_LATCHED)
            self.create_subscription(EstadoEstimado, '/estado', self.ao_estado, ros_util.QOS_FLUXO)
            self.create_subscription(TelemetriaMsg, '/dji/telemetria', self.ao_telemetria, ros_util.QOS_FLUXO)
            self.create_subscription(MapaLocal, '/mapa', self.ao_mapa, ros_util.QOS_CONFIAVEL)
            self.create_subscription(Alvos, '/alvos', self.ao_alvos, ros_util.QOS_FLUXO)
            self.create_timer(0.1, self.ao_temporizar)

        def ao_ativa(self, msg):
            self.ativa = msg.numero

        def ao_estado(self, msg):
            self.estado, self.t_estado = de_mensagem(Estado, msg), ros_util.agora()

        def ao_telemetria(self, msg):
            self.tel, self.t_tel = de_mensagem(Telemetria, msg), ros_util.agora()

        def ao_mapa(self, msg):
            self.mapa = MapaRecebido(msg)

        def ao_alvos(self, msg):
            self.visao = VisaoRecebida(msg, ros_util.agora())     # mensagens ROS não aceitam atributos novos

        def ao_temporizar(self):
            agora = ros_util.agora()
            tel = self.tel if self.t_tel is not None and agora - self.t_tel <= self.prazo_telemetria_s else None
            estado = self.estado
            if estado is not None and agora - self.t_estado > self.prazo_estado_s:
                estado = None
            setpoint, eventos = self.maquina.passo(agora, self.ativa, estado, tel, self.mapa, self.visao)
            if self.ativa == MaquinaTarefa2.NUMERO or setpoint.ativo:
                self.pub_setpoint.publish(ros_util.carimbar(self, copiar_campos(setpoint, SetpointMsg())))
            for ev in eventos:
                msg = copiar_campos(ev, EventoTarefa())
                msg.valor = float(ev.valor) if math.isfinite(ev.valor) else -1.0
                self.pub_evento.publish(ros_util.carimbar(self, msg))
                self.get_logger().info(f'{ev.tipo} [{ev.estado} {ev.nome_vertice}] {ev.detalhe}')

    rclpy.init(args=args)
    ros_util.executar(NoTarefa2())


if __name__ == '__main__':
    main()
