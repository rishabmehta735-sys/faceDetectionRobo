from setuptools import find_packages, setup

package_name = 'robot_face_core'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rishab',
    maintainer_email='rishab@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'talker = robot_face_core.talker:main',
            'camera_node = robot_face_core.camera_node:main',
            'face_recognition_node = robot_face_core.face_recognition_node:main',
            'voice_interface_node = robot_face_core.voice_interface_node:main',
            'gemini_llm_node = robot_face_core.gemini_llm_node:main',
        ],
    },
)
