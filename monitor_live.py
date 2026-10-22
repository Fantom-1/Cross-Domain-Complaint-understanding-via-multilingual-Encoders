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

    # 2. Evaluation History for Current Trial (Job 156, LR=2e-5)
    run_cmd("ACTIVE TRIAL 2 (Job 156) - ALL VALIDATION EVALUATION RESULTS", 
            "grep 'eval_f1_macro' /apps/cdcu/logs/slurm/cdcu-trial_lr2e5-156.out 2>/dev/null || echo 'No eval steps yet.'")

    # 3. Live Progress Bar & Step Speed
    run_cmd("ACTIVE TRIAL 2 (Job 156) - LIVE STEP PROGRESS & ETA", 
            "tail -n 5 /apps/cdcu/logs/slurm/cdcu-trial_lr2e5-156.err 2>/dev/null || echo 'No progress output.'")

    # 4. Recent Training Loss & LR Logs
    run_cmd("ACTIVE TRIAL 2 (Job 156) - RECENT TRAINING LOSS STEPS", 
            "tail -n 12 /apps/cdcu/logs/slurm/cdcu-trial_lr2e5-156.out 2>/dev/null || echo 'Waiting for log...'")

    # 5. Checkpoints Saved on Server
    run_cmd("SAVED CHECKPOINTS ON SERVER", 
            "ls -lhd /apps/cdcu/runs/*/trainer_output/checkpoint-* 2>/dev/null || ls -lh /apps/cdcu/runs/ 2>/dev/null")

    client.close()

if __name__ == "__main__":
    main()
