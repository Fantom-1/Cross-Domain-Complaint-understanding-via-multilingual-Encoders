"""Live Training Progress Monitor for CDCU Baseline Tuning.

Run this script anytime from your local machine:
    python monitor_live.py
"""
import paramiko
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "30.30.31.2"
USER = "abdul"
PASS = "abdul@332"
PORT = 22

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, port=PORT, username=USER, password=PASS,
                       look_for_keys=False, allow_agent=False, timeout=15)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    def run_cmd(title, cmd):
        print(f"\n{'='*70}\n[ {title} ]\n{'='*70}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        out = stdout.read().decode(errors='replace')
        if out.strip():
            print(out.strip())

    # 1. SLURM Queue
    run_cmd("SLURM QUEUE STATUS", "squeue -u abdul -o '%.8i %.9P %.18j %.8u %.2t %.10M %.6D %R'")

    # 2. Latest Training Metrics & Progress
    run_cmd("TRIAL 1 (LR=1e-5, Job 155) - LOGGED METRICS", 
            "tail -n 20 /apps/cdcu/logs/slurm/cdcu-trial_lr1e5-155.out 2>/dev/null || echo 'Waiting for log...'")

    # 3. Live Step Progress Bar & ETA
    run_cmd("TRIAL 1 (LR=1e-5, Job 155) - LIVE STEP & ETA", 
            "tail -n 15 /apps/cdcu/logs/slurm/cdcu-trial_lr1e5-155.err 2>/dev/null || echo 'No progress yet.'")

    # 4. Checkpoints Saved
    run_cmd("SAVED CHECKPOINTS", 
            "ls -lh /apps/cdcu/runs/trial_lr1e5_155/trainer_output 2>/dev/null || echo 'First evaluation checkpoint at step 250.'")

    client.close()

if __name__ == "__main__":
    main()
