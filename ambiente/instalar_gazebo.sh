#!/bin/bash
# Ambiente conda "ros_gz": ROS 2 Jazzy + Gazebo Harmonic (gz-sim 8) + ros_gz, SEM sudo (RoboStack, conda-forge).
# Alternativa com sudo no Ubuntu 24.04 / Mint 22: sudo apt install ros-jazzy-desktop ros-jazzy-ros-gz
# Depois: compila o workspace em pastas separadas (build_gz/install_gz) para não misturar com o ROS do sistema.
set -e
CONDA=${CONDA:-$HOME/miniforge3}
source "$CONDA/etc/profile.d/conda.sh"
if ! conda env list | grep -q "^ros_gz "; then
    "$CONDA/bin/mamba" create -y -n ros_gz -c conda-forge -c robostack-jazzy \
        ros-jazzy-ros-base ros-jazzy-ros-gz ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-default-plugins \
        ros-jazzy-launch-ros colcon-common-extensions opencv numpy pyyaml pytest cmake pkg-config make compilers
fi
conda activate ros_gz
cd "$(dirname "$0")/../ros2_ws"
colcon --log-base log_gz build --build-base build_gz --install-base install_gz
echo
echo "Pronto. Em cada terminal:"
echo "  source $CONDA/etc/profile.d/conda.sh && conda activate ros_gz && source $(pwd)/install_gz/setup.bash"
