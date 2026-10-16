"""Разведка/эксперименты медиа. Сейчас: тестовый ролик (scripts/video_demo.py, стадия — третья строка trigger/tg). Ничего не постит."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lines = open(os.path.join(ROOT, "trigger", "tg")).read().split("\n")
stage = (lines[2].strip() if len(lines) > 2 else "") or "stage1"
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "video_demo.py"), stage])
