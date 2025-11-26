import subprocess, shutil, os, sys

class Config:
    IP = "127.0.0.1"   # valeur par défaut
    PORT = 5000        # valeur par défaut

class Utils:

    MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def get_hash(ref):
        return subprocess.check_output(
            ['git', 'rev-parse', ref],
            cwd=Utils.MODULE_ROOT
            ).decode().strip()

    def hashCheck():
        subprocess.run(
            ['git', 'fetch'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=Utils.MODULE_ROOT
        )

        # Courante
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=Utils.MODULE_ROOT
        ).decode().strip()

        # Hash local & distant
        local_hash = Utils.get_hash('HEAD')
        remote_hash = Utils.get_hash(f'origin/{branch}')

        if local_hash != remote_hash:
            print("Please update the code : git pull origin main")
            os._exit(1)

    def gitCheck():
        if shutil.which("git") is None:
            print("Please install git")
            os._exit(1)