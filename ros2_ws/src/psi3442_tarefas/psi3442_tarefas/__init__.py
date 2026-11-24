"""Sistema de Missões Autônomas com DJI Mini 4 Pro — PSI3442 P2 2026.

Cada módulo corresponde a uma folha do nível n (modelo_sysml/03_NivelN.sysml). A lógica fica em classes sem
dependência de ROS 2 (testáveis com pytest em qualquer máquina); os nós rclpy são invólucros finos em main().
"""
