import subprocess, shutil

class Config:
    IP = "127.0.0.1"   # valeur par défaut
    PORT = 5000        # valeur par défaut

class Utils:
    def get_hash(ref):
        return subprocess.check_output(['git', 'rev-parse', ref]).decode().strip()

    def hashCheck():
        # Hash local
        local_hash = Utils.get_hash('HEAD')

        # Récupérer les infos du remote
        subprocess.run(['git', 'fetch'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Détecter la branche courante
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()

        # Hash distant
        remote_hash = Utils.get_hash(f'origin/{branch}')

        if local_hash != remote_hash:
            print("Please update the code : git pull")
            exit(1)

    def gitCheck():
        if shutil.which("git") is None:
            print("Please install git")
            exit(1)