from setuptools import find_packages, setup

package_name = 'manipulator'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/simulation.launch.py']),
        ('share/' + package_name + '/urdf', ['urdf/manipulator.urdf']),
        ('share/' + package_name + '/config', ['config/controllers.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='dell',
    maintainer_email='dell@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gui_to_trajectory = manipulator.gui_to_trajectory:main',
        ],
    },
)
