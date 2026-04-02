from setuptools import find_packages, setup
from typing import List

def get_requirements() -> List[str]:
    try:
        with open('requirements.txt', 'r', encoding='utf-8-sig') as file:
            requirement_list = [
                line.strip() for line in file.readlines()
                if line.strip()
                and not line.strip().startswith('-e')
                and not line.strip().startswith('#')
                and not line.strip().startswith('file://')
            ]
        return requirement_list
    except FileNotFoundError:
        print("requirements.txt not found!")
        return []

setup(
    name="Multi_Agentic_Booking_Doctors_email",
    version="0.0.1",
    author="harshit nehra",
    author_email="nehraharshit01@gmail.com",
    packages=find_packages(),
    install_requires=get_requirements(),
    python_requires=">=3.10",
)