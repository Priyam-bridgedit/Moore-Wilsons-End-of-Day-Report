import sys
from cx_Freeze import setup, Executable

# GUI applications require a different base on Windows
# the default is for a console application.
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Build options
build_options = {
    'packages': ['os', 'tkinter', 'pandas', 'pyodbc', 'configparser', 'apscheduler'],
    'excludes': [],
    'include_files': ['config.ini'],  # Include the config.ini file
}

# Executable options
executables = [
    Executable(
        script='EOD.py',  # This is the target script for the first executable
        base=base,
        targetName='End Of Day Sales.exe',  
    )
]

# Create the setup
setup(
    name='Sales Report',  # Name of the application
    version='1.0',
    description='Sales Report',
    options={'build_exe': build_options},
    executables=executables,
)
