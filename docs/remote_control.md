# Control the manipulator simulation from another PC

This guide runs Gazebo and the ROS 2 controllers on a simulation PC, and uses a second PC on the same Wi-Fi to control the simulated arm. It covers remote Joint State Publisher sliders and direct ROS 2 trajectory commands.

## How the pieces connect

The simulation PC runs Gazebo, `robot_state_publisher`, the joint state broadcaster, the arm and gripper trajectory controllers, and the `gui_to_trajectory` bridge. The controller PC publishes slider values on `/joint_states_gui`. The bridge converts those values into commands on `/arm_controller/joint_trajectory` and `/gripper_controller/joint_trajectory`.

```text
Controller PC: Joint State Publisher GUI
                  │ publishes /joint_states_gui
                  ▼
Simulation PC: gui_to_trajectory bridge
                  │ publishes trajectory commands
                  ▼
Simulation PC: ros2_control → Gazebo manipulator
```

The simulation PC is the only machine that needs to run the bridge. A visible topic list confirms ROS graph discovery; checking topic messages confirms that slider and command data actually flows.

## Requirements

- Both PCs have ROS 2 Jazzy installed and use the same ROS domain and RMW implementation.
- Both are connected to the same Wi-Fi subnet. The Wi-Fi access point must allow devices to communicate and pass DDS multicast; guest networks and client/AP isolation can prevent this.
- The simulation PC uses WSL 2 mirrored networking if ROS runs inside WSL. In `%USERPROFILE%\.wslconfig`, configure:

  ```ini
  [wsl2]
  networkingMode=mirrored
  ```

  After changing `.wslconfig`, restart WSL from PowerShell with `wsl --shutdown`.
- The workspace is built and available on the simulation PC. The launch script sources `install/setup.bash` and sets its ROS networking variables.

## Configure ROS on both PCs

Use these settings in each ROS terminal. The simulation startup script sets them automatically; run the commands explicitly on the controller PC and in diagnostic terminals on either machine:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

To persist them on a Linux/Ubuntu controller PC, add these lines to `~/.bashrc` (avoid adding duplicates), open a new terminal, and check them with:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
```

Check the active settings with:

```bash
echo "$ROS_DISTRO $ROS_DOMAIN_ID $ROS_AUTOMATIC_DISCOVERY_RANGE $RMW_IMPLEMENTATION"
```

Expected output:

```text
jazzy 42 SUBNET rmw_fastrtps_cpp
```

The values must match on both PCs. Do not set `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` for this setup.

## Configure the simulation PC firewall for its current Wi-Fi

The Wi-Fi subnet can change when connecting to a different access point. Do not copy a subnet from an old network or type the literal placeholder `NEW_SUBNET_CIDR`; Windows will reject it. Determine the active interface and its IPv4 prefix first.

In regular PowerShell, list connected interfaces:

```powershell
Get-NetIPConfiguration |
  Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4DefaultGateway } |
  Select-Object InterfaceAlias,
    @{Name='IPv4';Expression={$_.IPv4Address.IPAddress}},
    @{Name='PrefixLength';Expression={$_.IPv4Address.PrefixLength}},
    @{Name='Gateway';Expression={$_.IPv4DefaultGateway.NextHop}}
```

Choose the active Wi-Fi interface (this workspace's current example is `Wi-Fi`). For example, IPv4 `10.21.86.209` with prefix length `24` belongs to `10.21.86.0/24`. The IP/prefix on another Wi-Fi can be different.

Open **PowerShell as Administrator**, set `$InterfaceAlias` to the Wi-Fi interface name reported above, and run this block. It calculates the subnet from that interface instead of relying on a manually edited CIDR. It recreates only the rule named `ROS2Domain42`, allowing UDP ports `17900–17999` from that subnet:

```powershell
$InterfaceAlias = 'Wi-Fi'  # Replace if Windows reports a different Wi-Fi interface name.
$ip = Get-NetIPAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '169.254.*' } |
  Select-Object -First 1
if (-not $ip) { throw "No IPv4 address found on interface $InterfaceAlias" }

$remaining = [int]$ip.PrefixLength
$networkOctets = foreach ($octet in $ip.IPAddress.Split('.')) {
  $bits = [Math]::Min(8, [Math]::Max(0, $remaining))
  $mask = if ($bits -eq 0) { 0 } else { 256 - [Math]::Pow(2, 8 - $bits) }
  $remaining -= $bits
  ([int]$octet -band [int]$mask)
}
$subnet = '{0}/{1}' -f ($networkOctets -join '.'), $ip.PrefixLength
Write-Host "Allowing ROS 2 from $subnet"

Remove-NetFirewallHyperVRule -Name 'ROS2Domain42' -ErrorAction SilentlyContinue
New-NetFirewallHyperVRule `
  -Name 'ROS2Domain42' `
  -DisplayName 'ROS 2 Domain 42 from current Wi-Fi' `
  -Direction Inbound `
  -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' `
  -Protocol UDP `
  -LocalPorts '17900-17999' `
  -RemoteAddresses $subnet
```

If you prefer to enter a specific network manually, replace `$subnet` with a valid CIDR such as `'10.21.86.0/24'` in `-RemoteAddresses`. Use the subnet and prefix length for the Wi-Fi you are actually using. If Windows returns **Access is denied**, make sure the PowerShell window was opened with **Run as administrator**.

Check that the rule was created:

```powershell
Get-NetFirewallHyperVRule -Name 'ROS2Domain42' |
  Format-List Name,Direction,Protocol,LocalPorts,RemoteAddresses,Enabled
```

After changing the rule or `.wslconfig`, restart WSL:

```powershell
wsl --shutdown
```

If the controller PC is Linux and its UFW firewall is active, allow the domain's UDP ports from the same subnet (replace the example subnet if needed):

```bash
sudo ufw allow from 10.21.86.0/24 to any port 17900:17999 proto udp
```

## Start the simulation PC

From Ubuntu WSL, start Gazebo without its local slider window. The simulation and bridge stay on this PC:

```bash
bash /mnt/d/ros_manipulator_ws/src/manipulator/scripts/start_simulation.sh gui:=false
```

Leave this terminal and the simulation running. Wait for the robot and controllers to spawn.

## Start the controller PC slider GUI

On Ubuntu, install the GUI package once if needed:

```bash
sudo apt update
sudo apt install ros-jazzy-joint-state-publisher-gui
```

In a terminal with the ROS environment configured, start the GUI with the required topic remapping:

```bash
ros2 run joint_state_publisher_gui joint_state_publisher_gui --ros-args -r /joint_states:=/joint_states_gui
```

The GUI should receive `/robot_description` and show the manipulator joints. Move a slider to publish joint positions. Keep the simulation PC running. Do not launch another `gui_to_trajectory` bridge on the controller PC.

## Verify the complete command path

Run each check in a separate terminal. Set the ROS environment in the terminal first if it is not already configured.

1. On the controller PC, confirm the GUI is publishing and that positions change as sliders move:

   ```bash
   ros2 topic info /joint_states_gui --verbose
   ros2 topic echo /joint_states_gui
   ```

2. On the simulation PC, confirm the slider messages arrive:

   ```bash
   ros2 topic echo /joint_states_gui
   ```

3. On the simulation PC, confirm the bridge publishes arm commands when a slider moves:

   ```bash
   ros2 topic echo /arm_controller/joint_trajectory
   ```

   For the gripper, use:

   ```bash
   ros2 topic echo /gripper_controller/joint_trajectory
   ```

4. Check that controllers are active:

   ```bash
   ros2 control list_controllers
   ```

   `arm_controller` and `gripper_controller` should report `active`.

The controller PC is expected to publish `/joint_states_gui`, not the trajectory topics. The simulation PC's bridge converts the slider messages and publishes trajectories locally.

## Direct command alternative

Instead of the GUI, publish a trajectory from the controller PC. The controllers run on the simulation PC, so use the same domain settings on the controller terminal:

```bash
ros2 topic pub --once /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: [joint_1, joint_2, joint_3, joint_4, joint_5], points: [{positions: [0.5, 0.3, 0.2, -0.1, 0.0], time_from_start: {sec: 2}}]}"
```

```bash
ros2 topic pub --once /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{joint_names: [left_gear_joint], points: [{positions: [-0.5], time_from_start: {sec: 2}}]}"
```

## Troubleshooting

- **No simulation nodes or topics visible:** compare `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE`, and `RMW_IMPLEMENTATION` on both PCs; confirm the firewall rule uses the current Wi-Fi subnet; check Wi-Fi client/AP isolation or guest-network restrictions.
- **The GUI shows joints but `/joint_states_gui` has no publisher or no changing values:** ensure the GUI was started with the exact remapping command above, and inspect `ros2 topic info /joint_states_gui --verbose` on the controller PC.
- **Controller PC sees changing `/joint_states_gui`, but simulation PC does not:** ROS graph discovery is working, but message traffic is not reaching the simulation PC. Recheck its Hyper-V firewall rule and the Wi-Fi's device-to-device traffic restrictions.
- **Simulation PC receives `/joint_states_gui` but no trajectory messages appear:** confirm the launch terminal shows the bridge running and that the bridge node subscribes to `/joint_states_gui` (`ros2 node info /gui_to_trajectory`).
- **Trajectory messages appear but the arm does not move:** check `ros2 control list_controllers`, ensure Gazebo is running (not paused), and confirm the trajectory joint names match the controller configuration.
- **Topics appear in `ros2 topic list` but `ros2 topic echo` receives nothing:** graph discovery alone is not proof that user data is flowing; inspect the message path with the checks above and check firewall/network policy on both machines.
