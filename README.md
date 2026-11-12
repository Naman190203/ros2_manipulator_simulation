# ROS 2 manipulator simulation

## Start the simulation and live slider control

From Ubuntu WSL:

```bash
bash /mnt/d/ros_manipulator_ws/src/manipulator/scripts/start_simulation.sh
```

The startup script checks WSLg's graphics mode before opening the GUI. If WSLg has fallen back to copy mode, it restarts the WSLg compositor and waits for graphics redirection to recover first.

Gazebo opens with the Joint State Publisher GUI. The five arm sliders command the simulated arm. The `left_gear_joint` slider drives the gripper; Gazebo's ROS 2 control system applies the URDF mimic relationships to the paired gear, distal fingers, and parallel links. The GUI output uses `/joint_states_gui`, while Gazebo feedback remains on `/joint_states`.

The old `display.launch.py` visualization-only launch was removed; use the simulation launch above for the normal workflow.

## Control the simulation from another PC

See [docs/remote_control.md](docs/remote_control.md) for the two-PC ROS 2 setup, remote slider and direct trajectory control, network-specific firewall configuration, and troubleshooting.
