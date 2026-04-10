from setuptools import find_packages, setup

package_name = 'turtle_scanner'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mahefa-arry-tiana',
    maintainer_email='mahefa-arry-tiana@todo.todo',
    description='Balayage en serpentin et detection d une cible avec TurtleSim.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'spawn_target = turtle_scanner.spawn_target:main',
            'turtle_scanner_node = turtle_scanner.turtle_scanner_node:main',
            'mission_client = turtle_scanner.mission_client:main',
        ],
    },
)
