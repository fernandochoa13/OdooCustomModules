import os
import subprocess
import sys

class setup:
    """
    This Class installs required Packages or library
    """

    get_pckg = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
    installed_packages = [r.decode().split('==')[0] for r in get_pckg.split()]
    # List of your required packages
    required_packages = ['pandas', 'openpyxl']
    for packg in required_packages:
        if packg in installed_packages:
            pass
        else:
            print('installing package %s' % packg)
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', packg])