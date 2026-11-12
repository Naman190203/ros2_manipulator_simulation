#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash
workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$workspace/install/setup.bash"

# WSL 2.7.x can start WSLg in copy mode after a shared-memory failure.
# Repair that state before launching GUI clients so they do not open blank.
if [[ " $* " != *" gui:=false "* ]] && command -v wsl.exe >/dev/null 2>&1; then
  system_distro="${WSL_DISTRO_NAME:-Ubuntu-24.04}"
  gfx_state="$(
    wsl.exe -d "$system_distro" --system -- sh -c \
      "grep 'RDP backend: use_gfxredir' /mnt/wslg/weston.log | tail -1 | sed 's/.* = //' " \
      2>/dev/null | tr -d '\r'
  )"

  if [[ "$gfx_state" == "0" ]]; then
    echo "WSLg is in copy mode; restarting its compositor before opening the simulation GUI."
    wsl.exe -d "$system_distro" --system -- sh -c 'kill "$(pgrep -x weston)"' || true
    for _ in {1..15}; do
      sleep 1
      gfx_state="$(
        wsl.exe -d "$system_distro" --system -- sh -c \
          "grep 'RDP backend: use_gfxredir' /mnt/wslg/weston.log | tail -1 | sed 's/.* = //' " \
          2>/dev/null | tr -d '\r'
      )"
      [[ "$gfx_state" == "1" ]] && break
    done
    if [[ "$gfx_state" != "1" ]]; then
      echo "WSLg did not recover graphics redirection (state: ${gfx_state:-unknown})." >&2
      echo "Run from Windows PowerShell: wsl.exe -d $system_distro --system -- sh -c 'kill \$(pgrep -x weston)'" >&2
      exit 1
    fi
    echo "WSLg graphics redirection is active."
  fi
fi

# Keep this host and LAN ROS 2 clients in the same DDS discovery domain.
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

ros2 launch manipulator simulation.launch.py "$@"
