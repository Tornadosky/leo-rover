from glob import glob
from setuptools import find_packages, setup

package_name = "leo_collab_search"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/maps", glob("maps/*")),
        (f"share/{package_name}/worlds", glob("worlds/*")),
        (f"share/{package_name}/rviz", glob("rviz/*")),
        (f"share/{package_name}/scripts", glob("scripts/*")),
        (f"share/{package_name}/tools", glob("tools/*")),
        (f"share/{package_name}/docs", glob("docs/*")),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="Distributed Robotics Lab Team",
    maintainer_email="team@example.com",
    description="Two-Leo collaborative semantic/tag search starter package.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "logical_robot_sim = leo_collab_search.logical_robot_sim:main",
            "map_laser_sim = leo_collab_search.map_laser_sim:main",
            "fake_tag_detector = leo_collab_search.fake_tag_detector:main",
            "semantic_map_server = leo_collab_search.semantic_map_server:main",
            "room_search_manager = leo_collab_search.room_search_manager:main",
            "map_report = leo_collab_search.map_report:main",
            "smoke_drive = leo_collab_search.smoke_drive:main",
            "topic_snapshot = leo_collab_search.topic_snapshot:main",
            "object_detection_adapter = leo_collab_search.object_detection_adapter:main",
            "tf_topic_relay = leo_collab_search.tf_topic_relay:main",
        ],
    },
)
