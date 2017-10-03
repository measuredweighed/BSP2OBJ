from setuptools import setup

setup(name='bsp2obj',
      version='0.2',
      description='A utility for converting BSP maps to the OBJ/MTL file format',
      url='https://github.com/measuredweighed/BSP2OBJ',
      author='@measuredweighed',
      license='MIT',
      packages=['bsp2obj'],
      install_requires=[
          'pillow',
          'enum'
      ],
      entry_points={
          'console_scripts':['bsp2obj=bsp2obj.command_line:main']
      },
      zip_safe=False)