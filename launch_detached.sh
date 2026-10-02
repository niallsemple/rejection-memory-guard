#!/bin/bash
# Start the driver in its own session so it survives the parent shell. Usage: [END_STEP=NN] [START_STEP=NN] ./launch_detached.sh
cd "$(dirname "$0")"
python3 - <<'PY'
import os, subprocess
log = open("build.log", "ab")
p = subprocess.Popen(["nohup", "caffeinate", "-dimsu", "./run_build.sh"], stdin=subprocess.DEVNULL,
                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=os.environ.copy())
open(".driver.pid", "w").write(str(p.pid))
print("driver pid", p.pid)
PY
