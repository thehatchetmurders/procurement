
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def run_script(script, env=None):
    print(f"\n>>> Running {script}", flush=True)

    subprocess.run(
        [sys.executable, str(BASE_DIR / script)],
        check=True,
        env=env,
        cwd=BASE_DIR,
    )


def main():
    refresh_env = os.environ.copy()
    refresh_env["REFRESH_CONTRACTS"] = "1"

    plans_env = os.environ.copy()
    plans_env["REFRESH_PLANS"] = "1"

    run_script("main.py", env=refresh_env)
    run_script("import_contracts.py")
    run_script("fetch_plans.py", env=plans_env)
    run_script("import_plans.py")

    print("\nREFRESH FINISHED")


if __name__ == "__main__":
    main()
