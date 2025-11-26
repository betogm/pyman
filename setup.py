# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

# Autor e Licença extraídos dos seus scripts
AUTHOR = "Huberto Gastal Mayer"
EMAIL = "hubertogm@gmail.com"
LICENSE = "GPLv3"
DESCRIPTION = "PyMan - A CLI tool for executing HTTP request collections defined in YAML"

setup(
    name="pyman",
    version="0.2.0",
    description=DESCRIPTION,
    long_description=f"{DESCRIPTION}. Criado por {AUTHOR}.",
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    
    # Em vez de 'py_modules', usamos 'packages'
    # find_packages() encontra automaticamente o diretório 'pyman'
    # que contém o __init__.py
    packages=find_packages(),
    
    # Dependências necessárias (já estava correto com Faker)
    install_requires=[
        'requests',
        'PyYAML',
        'Faker',
    ],
    
    # Isso cria o comando 'pyman' no terminal
    entry_points={
        'console_scripts': [
            'pyman=pyman.pyman:main',
        ],
    },
    
    # Classificadores para informar o PyPI (opcional, mas boa prática)
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Testing',
    ],
    python_requires='>=3.7',
)