import os
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


def run_script(script_path, *args):
    """
    Run a python script with the current interpreter (the venv python when started from the venv).
    Arguments are passed directly, nothing is written to disk.
    :param script_path : path of the script relative to the project root
    :param args : command line arguments for the script
    :return : exit code of the script
    """
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, script_path)] + [str(a) for a in args]
    return subprocess.call(cmd, cwd=PROJECT_ROOT)
