"""Тест вертикального ролика «Наши рвут НХЛ» (30 с, 1080×1920): клипы НХЛ + наши карточки + нейроозвучка (edge-tts).
stage1 — скачать клипы хет-трика и сделать контактные листы кадров (чтобы выбрать момент гола) + пробная озвучка.
stage2 — собрать ролик по таймингу. Результат — tg/demo/. Ничего не постит."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import media
OUT = os.path.join(ROOT, "tg", "demo")
TMP = "/tmp/demo"
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
LOG = {"ok": [], "fail": []}
D = json.load(open(os.path.join(ROOT, "site", "data.json")))
HT = next(x for x in D["highlights"]["items"] if x["kind"] == "hattrick")
CLIPS = [c["id"] for c in HT["clips"]]

def sh(cmd, t=600):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    if r.returncode:
        LOG["fail"].append((cmd[:80], r.stderr[-300:]))
    return r.stdout

def stage1():
    media.tools(LOG)
    info = {}
    for i, cid in enumerate(CLIPS):
        fn = media.clip(cid, TMP)
        if not fn:
            LOG["fail"].append(f"clip {cid}"); continue
        w, h, d = media.probe(fn)
        info[cid] = dict(w=w, h=h, d=d)
        # контактный лист: кадр каждую секунду, подпись времени
        sh(f"ffmpeg -y -loglevel error -i {fn} -vf \"fps=1,scale=320:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=22:fontcolor=yellow:box=1:boxcolor=black,tile=6x{(d // 6) + 1}\" -frames:v 1 {OUT}/sheet_{i}.jpg")
    sh("pip install -q edge-tts")
    sh(f"edge-tts --voice ru-RU-DmitryNeural --rate=+8% --text 'Наши рвут НХЛ! Проверка голоса.' --write-media {OUT}/voice_test.mp3")
    json.dump(dict(info=info, log=LOG), open(f"{OUT}/stage1.json", "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    {"stage1": stage1}[sys.argv[1] if len(sys.argv) > 1 else "stage1"]()
