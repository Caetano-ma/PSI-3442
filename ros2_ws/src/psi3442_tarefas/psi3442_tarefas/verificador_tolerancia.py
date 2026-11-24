"""VerificadorTolerancia (nível n): veredito de P05.

dentro = |erro horizontal| <= tolHorizontal e |erro vertical| <= tolVertical e |v| <= vPairadoMax.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Veredito:
    dentro_horizontal: bool
    dentro_vertical: bool
    dentro_velocidade: bool
    erro_horizontal_m: float
    erro_vertical_m: float
    velocidade_mps: float

    @property
    def dentro(self):
        return self.dentro_horizontal and self.dentro_vertical and self.dentro_velocidade


FORA = Veredito(False, False, False, math.inf, math.inf, math.inf)


class VerificadorTolerancia:
    def __init__(self, tol_horizontal_m, tol_vertical_m, v_pairado_max_mps):
        self.tol_horizontal_m = tol_horizontal_m
        self.tol_vertical_m = tol_vertical_m
        self.v_pairado_max_mps = v_pairado_max_mps

    def avaliar(self, estado, setpoint):
        if estado is None or setpoint is None or not estado.valido:
            return FORA
        erro_h = math.hypot(estado.x_m - setpoint.x_m, estado.y_m - setpoint.y_m)
        erro_v = abs(estado.z_m - setpoint.z_m)
        velocidade = math.sqrt(estado.vx_mps ** 2 + estado.vy_mps ** 2 + estado.vz_mps ** 2)
        return Veredito(
            dentro_horizontal=erro_h <= self.tol_horizontal_m,
            dentro_vertical=erro_v <= self.tol_vertical_m,
            dentro_velocidade=velocidade <= self.v_pairado_max_mps,
            erro_horizontal_m=erro_h,
            erro_vertical_m=erro_v,
            velocidade_mps=velocidade,
        )
