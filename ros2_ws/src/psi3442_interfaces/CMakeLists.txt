cmake_minimum_required(VERSION 3.8)
project(psi3442_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ComandoOperador.msg"
  "msg/TarefaAtiva.msg"
  "msg/StatusTarefa.msg"
  "msg/EventoTarefa.msg"
  "msg/ComandoDiscreto.msg"
  "msg/Setpoint.msg"
  "msg/EstadoEstimado.msg"
  "msg/Telemetria.msg"
  "msg/ComandoVelocidade.msg"
  "msg/Falha.msg"
  "msg/DeteccaoBalao.msg"
  "msg/Alvos.msg"
  "msg/BalaoMapa.msg"
  "msg/MapaLocal.msg"
  DEPENDENCIES builtin_interfaces std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
