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
HT = next((x for x in D["highlights"]["items"] if x["kind"] == "hattrick"), None)
CLIPS = [c["id"] for c in HT["clips"]] if HT else []

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


# ---------------------------------------------------------------- стадия 2: сборка
W, H = 1080, 1920
VOICE = ("ru-RU-DmitryNeural", "+12%", "+6Hz")
MUSIC = ("Big Rock", 6.0)  # Kevin MacLeod (incompetech.com), CC BY 4.0 — указать в описании
SCENES = [
    dict(kind="title", say="Наши рвут НХЛ!"),
    dict(kind="video", say="Марченко — хет-трик, первый за «Торонто»!", stat="3 гола за вечер",
         cuts=[(6406931425112, 37.0, 4.5), (6406935824112, 41.0, 3.0)], chip="Хет-трик", name="Кирилл Марченко", team="TOR"),
    dict(kind="video", say="Капризов — гол и две передачи. Уже девять шайб в восьми матчах!", stat="1 гол · 2 передачи",
         cuts=[(6406938424112, 32.5, 4.5), (6406938424112, 44.0, 2.5)], chip="Гол + 2 передачи", name="Кирилл Капризов", team="MIN"),
    dict(kind="video", say="Барбашёв раздаёт: три голевые в разгроме «Калгари»!", stat="3 передачи · «Вегас» 6:2",
         cuts=[(6406945716112, 35.0, 6.0)], chip="3 передачи", name="Иван Барбашёв", team="VGK"),
    dict(kind="cta", say="Все наши в НХЛ — на эн-эйч-эл стэтс точка ру и в нашем телеграме.",
         show="Все наши в НХЛ — на NHL&#8209;STATS.RU и в Telegram"),
]
PRESETS = {
    "nashi": dict(scenes=None, title_bg=(0, 42), out="nashi_rvut_nhl_v3.mp4"),
    "ovi": dict(title_bg=(6371144441112, 17.5), out="ovechkin_930.mp4", scenes=[
        dict(kind="title", chip_t="легенда в цифрах", fs=170, lines='ОВЕЧКИН<br><span style="color:#FF4A55">930</span><br>ГОЛОВ', say="Девятьсот тридцать голов в НХЛ. Александр Овечкин!"),
        dict(kind="video", chip="Гол № 895", name="Александр Овечкин", team="WSH", stat="6 апреля 2025 · рекорд Гретцки побит",
             say="Апрель двадцать пятого: восемьсот девяносто пятый гол, и рекорд Уэйна Гретцки побит. Сам Гретцки аплодирует на трибуне.",
             cuts=[(6371144441112, 6.0, 3.2), (6371144441112, 17.0, 2.2), (6371144441112, 26.0, 3.6)]),
        dict(kind="video", chip="Сезон 2026/27", name="Александр Овечкин", team="WSH", stat="1 гол · 10 бросков · 7 матчей",
             say="А новый сезон начался тяжело: один гол и всего десять бросков за семь матчей.",
             cuts=[(6406659994112, 6.5, 3.0), (6406659994112, 18.0, 2.0)]),
        dict(kind="card", player="Alex Ovechkin", name="Александр Овечкин", team="WSH", big="13:56", bfs=200, unit="в среднем на льду за матч",
             sub="за карьеру — 20:25", say="И играет он почти на семь минут меньше, чем привык за карьеру."),
        dict(kind="cta", say="Следим за каждым матчем Овечкина и всех наших: эн-эйч-эл стэтс точка ру и наш телеграм.",
             show="Следим за каждым матчем Овечкина — NHL&#8209;STATS.RU и Telegram"),
    ]),
}
FONTS = os.path.join(ROOT, "scripts", "cards", "fonts")
CSS = f"""@font-face{{font-family:G;src:url(file://{FONTS}/GolosText.ttf)}}@font-face{{font-family:F;src:url(file://{FONTS}/FiraSansExtraCondensed-ExtraBold.ttf);font-weight:800}}
*{{margin:0;padding:0;box-sizing:border-box}}html,body{{width:{W}px;height:{H}px;overflow:hidden;background:transparent;font-family:G;color:#fff}}
.brand{{position:absolute;left:60px;top:70px;display:flex;align-items:center;gap:16px;font-family:F;font-weight:800;font-size:44px;letter-spacing:.03em;text-shadow:0 4px 18px rgba(0,0,0,.6)}}
.brand img{{width:68px;height:68px}}.brand span{{color:#FF4A55}}
.sub{{position:absolute;left:60px;right:60px;bottom:230px;font-family:F;font-weight:800;font-size:58px;line-height:1.12;text-align:center;
  background:rgba(11,13,17,.72);border-radius:24px;padding:22px 30px;text-wrap:balance}}
.chip{{display:inline-block;font-family:F;font-weight:800;font-size:46px;letter-spacing:.08em;text-transform:uppercase;background:#FF4A55;color:#fff;border-radius:14px;padding:6px 22px}}
"""
TEAMC = {"TOR": "#00205B", "MIN": "#154734", "VGK": "#B4975A", "WSH": "#8F0A1F"}

def mark():
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(open(os.path.join(ROOT, "site", "logo-mark.svg"), "rb").read()).decode()

def html_for(sc):
    brand = f'<div class="brand"><img src="{mark()}">NHL-STATS<span>.RU</span></div>'
    sub = f'<div class="sub">{sc.get("show") or sc["say"]}</div>'
    if sc["kind"] == "title":
        return f"""<style>{CSS}</style>{brand}<div style="position:absolute;left:60px;right:60px;top:620px;text-align:center">
<div class="chip">{sc.get('chip_t', 'ночь на 16 октября')}</div><h1 style="font-family:F;font-weight:800;font-size:{sc.get('fs', 190)}px;line-height:.92;margin-top:40px;text-shadow:0 10px 40px rgba(0,0,0,.6)">{sc.get('lines', 'НАШИ<br><span style="color:#FF4A55">РВУТ</span><br>НХЛ')}</h1></div>"""
    if sc["kind"] == "video":
        return f"""<style>{CSS}</style>{brand}<div style="position:absolute;left:60px;right:60px;top:330px;text-align:center"><span class="chip">{sc['chip']}</span>
<div style="font-family:F;font-weight:800;font-size:96px;margin-top:22px;text-shadow:0 6px 24px rgba(0,0,0,.7)">{sc['name']}</div>
<div style="font-size:46px;color:#E2E5EA;margin-top:6px;text-shadow:0 4px 18px rgba(0,0,0,.8)">{sc.get('stat', '')}</div></div>{sub}"""
    if sc["kind"] == "card":
        hp = D["heads"].get(sc["player"])
        c = TEAMC.get(sc["team"], "#1a1f27")
        return f"""<style>{CSS} body{{background:radial-gradient(1200px 1100px at 50% 30%,{c},#0B0D11 70%)}}</style>{brand}
<img src="https://assets.nhle.com/logos/nhl/svg/{sc['team']}_dark.svg" style="position:absolute;right:-160px;top:180px;width:760px;opacity:.12">
<img src="https://assets.nhle.com/mugs/nhl/{hp}.png" style="position:absolute;left:50%;transform:translateX(-50%);top:230px;width:620px;height:620px;border-radius:50%;object-fit:cover;object-position:50% 0;border:10px solid rgba(255,255,255,.25);background:{c}">
<div style="position:absolute;left:60px;right:60px;top:900px;text-align:center"><div style="font-family:F;font-weight:800;font-size:96px">{sc['name']}</div>
<div style="font-family:F;font-weight:800;font-size:{sc.get('bfs', 230)}px;line-height:1;color:#FF4A55;margin-top:10px">{sc['big']}</div>
<div style="font-size:52px;color:#E2E5EA">{sc['unit']}</div><div style="font-size:40px;color:#A9AFB8;margin-top:14px">{sc['sub']}</div></div>{sub}"""
    return f"""<style>{CSS} body{{background:radial-gradient(1100px 1100px at 50% 35%,#14335E,#0B0D11 70%)}}</style>
<div style="position:absolute;left:60px;right:60px;top:380px;text-align:center"><img src="{mark()}" style="width:260px;height:260px">
<div style="font-family:F;font-weight:800;font-size:150px;margin-top:30px">NHL-STATS<span style="color:#FF4A55">.RU</span></div>
<div style="font-size:50px;color:#C3C8CF;margin-top:16px">все наши в НХЛ · статистика · разборы</div>
<div style="display:inline-flex;align-items:center;gap:18px;margin-top:70px;background:#229ED9;border-radius:999px;padding:22px 46px;font-family:F;font-weight:800;font-size:64px">Telegram @nhlstatsru</div></div>{sub}<div style="position:absolute;left:0;right:0;bottom:120px;text-align:center;font-size:26px;color:#7A808A">Видео: NHL · Музыка: Kevin MacLeod (incompetech.com), CC BY 4.0</div>"""

def render_pngs():
    import tg
    tg.ensure_browser()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
        for i, sc in enumerate(SCENES):
            fn = f"{TMP}/s{i}.html"; open(fn, "w").write("<!doctype html><meta charset=utf-8>" + html_for(sc))
            pg.goto("file://" + fn, wait_until="networkidle"); pg.wait_for_timeout(500)
            pg.screenshot(path=f"{TMP}/s{i}.png", omit_background=True)
        b.close()

def dur(f):
    return float(sh(f"ffprobe -v error -show_entries format=duration -of csv=p=0 {f}").strip() or 0)

def stage2(preset="nashi"):
    global SCENES
    P = PRESETS[preset]
    if P['scenes']:
        SCENES = P['scenes']
    media.tools(LOG)
    sh("pip install -q edge-tts")
    render_pngs()
    ids = {c for sc in SCENES for c, _, _ in sc.get("cuts", [])} | (set(CLIPS) if not P['scenes'] else set()) | ({P['title_bg'][0]} if P['scenes'] else set())
    clips = {cid: media.clip(cid, TMP) for cid in ids}
    clips.update({i: clips[cid] for i, cid in enumerate(CLIPS) if cid in clips})
    segs, auds = [], []
    for i, sc in enumerate(SCENES):
        a = f"{TMP}/a{i}.mp3"
        for _ in range(4):
            sh(f"edge-tts --voice {VOICE[0]} --rate={VOICE[1]} --pitch={VOICE[2]} --text \"{sc['say']}\" --write-media {a}")
            if os.path.exists(a) and os.path.getsize(a) > 1000:
                break
            import time; time.sleep(8)
        ad = dur(a)
        if sc["kind"] == "video":
            parts = []
            target = max(ad + 0.4, min(sum(c[2] for c in sc['cuts']), ad + 1.6))  # после фразы — до 1,6 с картинки под музыку, без пустоты
            total = sum(c[2] for c in sc["cuts"])
            k_fit = min(1.0, target / total)  # длинные нарезки ужимаем под голос, короткие тянем последним кадром
            for k, (ci, ss, ln) in enumerate(sc["cuts"]):
                ln = round(ln * k_fit, 2)
                o = f"{TMP}/v{i}_{k}.mp4"
                sh(f"ffmpeg -y -loglevel error -ss {ss} -t {ln} -i {clips[ci]} -an -filter_complex "
                   f"\"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.15[bg];[0:v]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2,fps=30[v]\" "
                   f"-map [v] -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p {o}")
                parts.append(o)
            open(f"{TMP}/p{i}.txt", "w").write("".join(f"file '{x}'\n" for x in parts))
            raw = f"{TMP}/raw{i}.mp4"
            sh(f"ffmpeg -y -loglevel error -f concat -safe 0 -i {TMP}/p{i}.txt -c copy {raw}")
            ln = target
            seg = f"{TMP}/seg{i}.mp4"
            sh(f"ffmpeg -y -loglevel error -i {raw} -loop 1 -i {TMP}/s{i}.png -filter_complex \"[0:v]tpad=stop_mode=clone:stop_duration=5[b];[b][1:v]overlay=0:0,trim=duration={ln:.2f},setpts=PTS-STARTPTS[v]\" -map [v] -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -r 30 {seg}")
        else:
            ln = ad + (0.45 if sc["kind"] != "title" else 0.2)
            if sc["kind"] == "title":
                # фон — размытый кадр празднования
                sh(f"ffmpeg -y -loglevel error -ss {P['title_bg'][1]} -i {clips[P['title_bg'][0]]} -frames:v 1 {TMP}/t.jpg")
                src = f"-loop 1 -i {TMP}/t.jpg -loop 1 -i {TMP}/s{i}.png"
                fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=12:2,eq=brightness=-0.25,"
                      f"zoompan=z='1+0.0015*on':d=1:s={W}x{H}:fps=30[bg];[bg][1:v]overlay=0:0,trim=duration={ln:.2f}[v]")
            else:
                src = f"-loop 1 -i {TMP}/s{i}.png"
                fc = f"[0:v]scale={W*2}:{H*2},zoompan=z='1+0.0008*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,trim=duration={ln:.2f}[v]"
            seg = f"{TMP}/seg{i}.mp4"
            sh(f"ffmpeg -y -loglevel error {src} -filter_complex \"{fc}\" -map [v] -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -r 30 {seg}")
        sl = dur(seg)
        aa = f"{TMP}/aa{i}.wav"
        sh(f"ffmpeg -y -loglevel error -i {a} -af apad=whole_dur={sl:.3f} -ar 44100 -ac 2 {aa}")
        segs.append(seg); auds.append(aa)
    open(f"{TMP}/vs.txt", "w").write("".join(f"file '{x}'\n" for x in segs))
    open(f"{TMP}/as.txt", "w").write("".join(f"file '{x}'\n" for x in auds))
    sh(f"ffmpeg -y -loglevel error -f concat -safe 0 -i {TMP}/vs.txt -c copy {TMP}/v.mp4")
    sh(f"ffmpeg -y -loglevel error -f concat -safe 0 -i {TMP}/as.txt -c:a pcm_s16le {TMP}/a.wav")
    # музыка: свободный рок (CC BY), тише под голосом (sidechain), затухание в конце
    import urllib.parse, urllib.request
    mus = f"{TMP}/music.mp3"
    open(mus, "wb").write(urllib.request.urlopen(urllib.request.Request("https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + urllib.parse.quote(MUSIC[0]) + ".mp3",
                                                                        headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
    total = dur(f"{TMP}/v.mp4")
    sh(f"ffmpeg -y -loglevel error -i {TMP}/a.wav -ss {MUSIC[1]} -i {mus} -filter_complex "
       f"\"[1:a]atrim=duration={total:.2f},volume=0.55,afade=t=in:d=0.4,afade=t=out:st={total - 1.6:.2f}:d=1.6,aformat=sample_rates=44100:channel_layouts=stereo[m];"
       f"[0:a]asplit=2[v1][v2];[m][v2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[md];[v1][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]\" "
       f"-map [a] -c:a pcm_s16le {TMP}/mix.wav")
    sh(f"ffmpeg -y -loglevel error -i {TMP}/v.mp4 -i {TMP}/mix.wav -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart {OUT}/{P['out']}")
    for i in range(len(SCENES)):
        sh(f"cp {TMP}/s{i}.png {OUT}/overlay_{i}.png")
    json.dump(dict(len=dur(f"{OUT}/{P['out']}"), log=LOG), open(f"{OUT}/stage2.json", "w"), ensure_ascii=False, indent=1)

def stage3():
    """Клипы Капризова и передач Барбашёва (gamecenter) + контактные листы; пробы голосов."""
    media.tools(LOG)
    import urllib.request
    want = {2026020116: [("Kaprizov", "08:47")], 2026020118: [("Bowman", "11:03"), ("Stone", "01:06"), ("Stone", "12:10")]}
    found = {}
    for gid, goals in want.items():
        land = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api-web.nhle.com/v1/gamecenter/{gid}/landing", headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
        for per in (land.get("summary") or {}).get("scoring") or []:
            for x in per.get("goals") or []:
                ln = (x.get("lastName") or {}).get("default")
                for who, t in goals:
                    if ln == who and x.get("timeInPeriod") == t and x.get("highlightClip"):
                        found[f"{who}_{t.replace(':', '')}"] = x["highlightClip"]
    info = {}
    for k, cid in found.items():
        fn = media.clip(cid, TMP)
        if not fn:
            continue
        w, h, d = media.probe(fn)
        info[k] = dict(id=cid, d=d)
        sh(f"ffmpeg -y -loglevel error -i {fn} -vf \"fps=1,scale=320:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=22:fontcolor=yellow:box=1:boxcolor=black,tile=6x{(d // 6) + 1}\" -frames:v 1 {OUT}/sheet_{k}.jpg")
    sh("pip install -q edge-tts")
    txt = "Наши рвут НХЛ! Кирилл Марченко оформил первый хет-трик за «Торонто»."
    for v, r, pch in [("ru-RU-DmitryNeural", "+18%", "+6Hz"), ("ru-RU-DmitryNeural", "+25%", "+12Hz"), ("ru-RU-SvetlanaNeural", "+15%", "+4Hz"), ("ru-RU-DariyaNeural", "+15%", "+4Hz")]:
        sh(f"edge-tts --voice {v} --rate={r} --pitch={pch} --text \"{txt}\" --write-media {OUT}/voice_{v.split('-')[2]}_{r[1:-1]}.mp3")
    # Silero (офлайн, русские голоса)
    sh("pip install -q torch --index-url https://download.pytorch.org/whl/cpu && pip install -q omegaconf", 900)
    try:
        import torch
        m, _ = torch.hub.load("snakers4/silero-models", "silero_tts", language="ru", speaker="v4_ru", trust_repo=True)
        for spk in ("eugene", "aidar", "xenia"):
            a = m.apply_tts(text=txt, speaker=spk, sample_rate=48000)
            import wave, numpy as np
            pcm = (a.numpy() * 32767).astype("int16")
            with wave.open(f"{TMP}/sil_{spk}.wav", "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes(pcm.tobytes())
            sh(f"ffmpeg -y -loglevel error -i {TMP}/sil_{spk}.wav -b:a 96k {OUT}/voice_silero_{spk}.mp3")
    except Exception as ex:
        LOG["fail"].append(f"silero: {ex!r}"[:200])
    json.dump(dict(info=info, log=LOG), open(f"{OUT}/stage3.json", "w"), ensure_ascii=False, indent=1)


def sheets(ids):
    media.tools(LOG)
    for cid in ids:
        fn = media.clip(cid, TMP)
        if not fn:
            LOG["fail"].append(f"clip {cid}"); continue
        w, h, d = media.probe(fn)
        sh(f"ffmpeg -y -loglevel error -i {fn} -vf \"fps=1,scale=320:-2,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=22:fontcolor=yellow:box=1:boxcolor=black,tile=6x{(d // 6) + 1}\" -frames:v 1 {OUT}/sheet_{cid}.jpg")
    json.dump(dict(log=LOG), open(f"{OUT}/sheets.json", "w"), ensure_ascii=False, indent=1)


def goals(pid):
    """Все голы игрока в сезоне: клипы + контактные листы (для выбора момента) → tg/demo/goals_<pid>.json."""
    media.tools(LOG)
    import urllib.request
    G = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
    log = G(f"https://api-web.nhle.com/v1/player/{pid}/game-log/20262027/2").get("gameLog") or []
    res = []
    for g in sorted(log, key=lambda x: x["gameDate"]):
        if not g.get("goals"):
            continue
        land = G(f"https://api-web.nhle.com/v1/gamecenter/{g['gameId']}/landing")
        for per in (land.get("summary") or {}).get("scoring") or []:
            for x in per.get("goals") or []:
                if x.get("playerId") == pid:
                    res.append(dict(game=g["gameId"], date=g["gameDate"], opp=g.get("opponentAbbrev"), home=g.get("homeRoadFlag"),
                                    period=per.get("periodDescriptor", {}).get("number"), time=x.get("timeInPeriod"), strength=x.get("strength"),
                                    shot=x.get("shotType"), n=x.get("goalsToDate"), clip=x.get("highlightClip"), score=f"{x.get('awayScore')}:{x.get('homeScore')}"))
    for r in res:
        if r["clip"]:
            fn = media.clip(r["clip"], TMP)
            if fn:
                w, h, d = media.probe(fn); r["dur"] = d
                sh(f"ffmpeg -y -loglevel error -i {fn} -t 24 -vf \"fps=2,scale=240:-2,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black,tile=8x6\" -frames:v 1 {OUT}/sheet_{r['clip']}.jpg")
    json.dump(dict(goals=res, log=LOG), open(f"{OUT}/goals_{pid}.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "stage1"
    if a.startswith("goals:"):
        goals(int(a[6:]))
    elif a.startswith("sheets:"):
        sheets([int(x) for x in a[7:].split(",") if x])
    else:
        if a.startswith("stage2:"):
            stage2(a[7:])
        else:
            {"stage1": stage1, "stage2": stage2, "stage3": stage3}[a]()
