import subprocess
import sys
import os
import json

resco_dir = os.path.abspath(os.path.join("baselines", "RESCO"))
env = os.environ.copy()
env["PYTHONPATH"] = os.path.abspath(".") + os.pathsep + resco_dir

cmd = [
    sys.executable, "run_resco.py", "--algo", "MAXPRESSURE", "--scenario", "ideal"
]

print("Running command:", " ".join(cmd))
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
out, err = proc.communicate()
print("STDOUT:")
print(out)
print("STDERR:")
print(err)
print("RETURNCODE:", proc.returncode)

# Check if unified_metrics_ep1.json exists for maxpressure
import glob
print("\nMetrics files:")
for f in glob.glob("baselines/RESCO/results/**/*maxpressure*", recursive=True):
    print(f)
