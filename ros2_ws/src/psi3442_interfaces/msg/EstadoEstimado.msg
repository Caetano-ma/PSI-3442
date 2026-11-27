# /estado — estado da aeronave no ReferencialLocal (10 Hz, best effort).
# Origem no ponto de decolagem no piso; x para B (nariz na decolagem); y para D; z para cima.
builtin_interfaces/Time stamp
float64 x_m
float64 y_m
float64 z_m
float64 vx_mps
float64 vy_mps
float64 vz_mps
float64 psi0_graus              # guinada registrada na partida dos motores (define o referencial)
float64 guinada_local_graus     # guinada atual no ReferencialLocal (anti-horária a partir de +x) = psi0 - guinada
bool valido
string motivo_invalido
