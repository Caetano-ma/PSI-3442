"""T05 (P05): a contagem só conclui após 60 s contínuos depois de uma interrupção; interrupção registrada."""
import pytest

from psi3442_tarefas.cronometro_permanencia import CONCLUIDA, INICIADA, INTERROMPIDA, CronometroPermanencia

DT = 0.1


def alimentar(cronometro, t0, duracao, dentro):
    """Amostras a 10 Hz em [t0, t0 + duracao); devolve (instante final, lista de (t, resultado))."""
    resultados = []
    n = int(round(duracao / DT))
    for i in range(n):
        t = round(t0 + i * DT, 6)
        r = cronometro.atualizar(dentro, t)
        if r:
            resultados.append((t, r))
    return round(t0 + n * DT, 6), resultados


def test_t05_dentro_40s_fora_uma_amostra_dentro_60s():
    c = CronometroPermanencia(60.0)
    t, r1 = alimentar(c, 0.0, 40.0, True)
    assert r1 == [(0.0, INICIADA)]
    assert not c.concluida
    assert c.atualizar(False, t) == INTERROMPIDA          # uma única amostra fora
    assert c.interrupcoes == 1
    assert c.tentativas[0].duracao_s == pytest.approx(40.0)
    t_retorno = round(t + DT, 6)
    t, r2 = alimentar(c, t_retorno, 61.0, True)
    concluidas = [tt for tt, r in r2 if r == CONCLUIDA]
    assert len(concluidas) == 1
    # conclui na primeira amostra com >= 60 s contados desde o reinício (não desde o primeiro início);
    # o critério é estrito: com amostras a 10 Hz, até uma amostra depois dos 60 s
    assert 60.0 <= c.tentativas[-1].duracao_s <= 60.0 + DT + 1e-9
    assert c.tentativas[-1].inicio_s == t_retorno
    assert concluidas[0] - t_retorno == pytest.approx(c.tentativas[-1].duracao_s)
    assert c.concluida and c.tentativas[-1].concluida


def test_nao_conclui_antes_de_60s():
    c = CronometroPermanencia(60.0)
    _, resultados = alimentar(c, 0.0, 59.9, True)
    assert CONCLUIDA not in [r for _, r in resultados]
    assert c.decorrido(59.8) == pytest.approx(59.8)


def test_varias_interrupcoes_registradas():
    c = CronometroPermanencia(60.0)
    t = 0.0
    for _ in range(3):
        t, _ = alimentar(c, t, 10.0, True)
        t, _ = alimentar(c, t, 0.5, False)
    assert c.interrupcoes == 3
    assert [round(x.duracao_s, 6) for x in c.tentativas] == [10.0, 10.0, 10.0]


def test_zerar_e_relogio_nao_monotonico():
    c = CronometroPermanencia(5.0)
    alimentar(c, 0.0, 6.0, True)
    assert c.concluida
    c.zerar()
    assert not c.concluida and c.tentativas == []
    c.atualizar(True, 10.0)
    with pytest.raises(ValueError):
        c.atualizar(True, 9.0)


def test_apos_concluir_nao_emite_mais():
    c = CronometroPermanencia(1.0)
    alimentar(c, 0.0, 1.2, True)
    assert c.atualizar(False, 2.0) is None
    assert c.atualizar(True, 2.1) is None
