import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('manipulator')
    urdf = os.path.join(share, 'urdf', 'manipulator.urdf')
    controllers = os.path.join(share, 'config', 'controllers.yaml')
    robot_description = Command([
        'xacro ', urdf, ' controllers_file:=', controllers
    ])

    gazebo = IncludeGazebo()
    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
            'use_robot_description_topic': True,
        }],
        output='screen',
    )
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )
    slider_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        parameters=[{'robot_description': robot_description}],
        remappings=[('/joint_states', '/joint_states_gui')],
        condition=IfCondition(LaunchConfiguration('gui')),
        output='screen',
    )
    gui_controller = Node(
        package='manipulator',
        executable='gui_to_trajectory',
        output='screen',
    )
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-string', robot_description, '-name', 'manipulator'],
        output='screen',
    )
    jsb = Node(
        package='controller_manager', executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )
    arm = Node(
        package='controller_manager', executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )
    gripper = Node(
        package='controller_manager', executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )
    return LaunchDescription([
        DeclareLaunchArgument('gz_args', default_value='-r -v 3 empty.sdf'),
        DeclareLaunchArgument('gui', default_value='true'),
        gazebo,
        clock_bridge,
        state_publisher,
        slider_gui,
        gui_controller,
        TimerAction(period=3.0, actions=[spawn]),
        TimerAction(period=8.0, actions=[jsb, arm, gripper]),
    ])


def IncludeGazebo():
    from launch.actions import IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource
    from launch.substitutions import PathJoinSubstitution
    from launch_ros.substitutions import FindPackageShare

    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items(),
    )
