#!/usr/bin/env python3
"""Модель прогнозов «Сводки НХЛ», версия 4.

Запуск:  python3 model.py archive.json data.json prior.json > model.json
(prior.json: рейтинги команд и вратари прошлого сезона)

Кэфы в расчёт не входят: модель считает по матчам, ожидаемым голам, вратарям, травмам и усталости,
а рынок используется только в конце для сравнения.

1. Сила команд. Атака и оборона каждой команды — пуассоновская регрессия по матчам сезона с учётом
   соперников и своей площадки. Цель для каждого матча — смесь: 30% реальных голов и 70% ожидаемых
   голов (xG MoneyPuck, средние команды за сезон на сегодня, поле team_xg в data.json). Если team_xg
   нет — только голы. Оценки притянуты к уровню прошлого сезона (65% прошлогоднего отличия, рейтинги
   по той же смеси xG и голов) с силой 30 «матчей».
2. Усталость. Второй матч за два дня против отдохнувшего соперника: −6% к голам уставшей команды и +6%
   к голам соперника.
3. Калибровка. Вероятность победы чуть «растягивается» от 50% (коэффициент 1,1 к логиту): модель на
   истории систематически недооценивала явных фаворитов.
   Проверка вслепую на 5 сезонах 2021–2026 по матчам MoneyPuck (каждый день — только прошлые матчи):
   угаданные исходы против версии 2 — 64,3/62,4, 63,2/60,7, 61,2/59,8, 59,9/58,3, 54,3/53,8 (%);
   лог-лосс лучше во всех пяти сезонах. Серии побед и «везение» (голы минус xG) после учёта xG
   ничего не добавляют — проверено, не используются.
4. Вратарь. Класс вратаря = сейвы сверх ожидаемого (xG против минус пропущенные) на единицу xG
   за прошлые сезоны (вес 0,8 за каждый сезон назад) и этот сезон (goalie_xg в data.json), сильно
   притянутый к нулю. Голы соперника умножаются на 1 − 0,5 × класс (в пределах ±10%).
   Проверено по броскам MoneyPuck 2021–2026: эффект небольшой, чуть лучше прогноз тоталов; то, что
   в воротах сменщик, само по себе почти ничего не меняет, проигрывают из-за усталости команды.
5. Травмы и состав. Подтверждённые (Out, IR, LTIR) игроки. Ценность игрока — личный xG за матч
   (этот сезон, skater_xg в data.json, плюс прошлые, players_ixg в prior.json, не больше 20 матчей).
   Проверено по броскам MoneyPuck 2021–2026 (отсутствие лидера = ни одной попытки броска в матче и в
   соседнем; на 2021–2023 сверено с реальным временем на льду): за единицу личного xG отсутствующего
   команда забивает ~0,45 гола меньше и пропускает ~0,4 больше; «свежая» и давняя потеря весят одинаково. Лог-лосс лучше в 4
   сезонах из 5. Ключевые = топ-6 своей команды по личному xG за матч (не ниже 0,12). Защитники по xG
   почти не видны, поэтому выпавший защитник из топ-4 команды по времени на льду (toi в skaters, этот
   сезон, от 3 игр) стоит ±0,012 гола за каждую минуту сверх 16 (защитник с 24 минутами ≈ −0,1 гола
   своей атаке и +0,1 сопернику; оценено по реальному времени на льду 2021–2023, коэффициент взят
   осторожно); у защитника берётся большее из двух. Давно выбывший при 20+ сыгранных командой матчах —
   с половинным весом. Нет xG — оценка по очкам за матч.
   Спецбригады отдельно (большинство/меньшинство/5 на 5, дисциплина, реализация в большинстве) проверены
   и ничего не добавляют к общему xG — не используются.
6. Ничья и овертайм. Независимый Пуассон даёт ~16% ничьих в основное время, в НХЛ их 20–25%:
   шанс ничьей умножается на 1,35. После ничьей хозяева выигрывают 0,517 + 0,45 × (перевес в основное
   время): в 3 на 3 сильнейший выигрывает заметно чаще, буллиты — монетка (проверено на 1450 матчах).
7. Рынок. Сравнение с закрывающими линиями 2021–2023 (архив SportsbookReviewsOnline): рынок точнее
   модели в целом (65,3% против 64,4% угаданных), и когда они расходятся больше чем на 4 п.п., прав
   почти всегда рынок. Исключение — усталость: гостей на бэк-ту-бэке рынок недооценивал против
   хозяев. Поэтому итог p_*_blend = 70% рынка + 30% модели, а поле fatigue_edge отмечает матчи, где
   у модели есть причина спорить с линией.
8. Тихоокеанская площадка. Перелёты, часовые пояса, высота (Денвер, Солт-Лейк), длина выездной серии,
   первый матч после выезда — проверены по 6200 матчам 2021–2026, время начала (дневные и поздние матчи)
   — по 2400 матчам 2021–2023; сверх усталости почти ничего не дают.
   Устойчиво одно: хозяева с Тихоокеанского побережья (ANA, LAK, SEA, SJS, VAN, VGK) выигрывают дома
   реже, чем по силе им положено (−4 п.п., в 4 сезонах из 5), сильнее всего у слабых команд; рынок
   2021–2023 их тоже переоценивал. Поправка осторожная: −2,5% к голам хозяев и +2,5% к голам гостей
   (оптимум на истории ~4%). Лог-лосс лучше в 4 сезонах из 5.
9. Российские конторы. Честная вероятность = итог p_*_blend (рынок + модель); для тотала — смесь рынка
   и модели на линии Pinnacle, сдвинутая моделью на линию конторы. 1xBet (odds_1x) — исход основного
   времени: шанс ничьей берётся из его же линии. Другие конторы — из upcoming[].books (например,
   marathonbet). В soft попадают ставки, где кэф выше честного минимум на 3%. У трёхисходных контор
   (есть «ничья») тотал тоже считается за основное время: при линии 6,5 ничья 3:3 у них — меньше, а не
   больше; это учтено (иначе их ТБ 6,5 выглядел бы ложно выгодным), целые линии у них не оцениваются.
10. Версия 4 (единый стенд: всё как на сайте, 5 сезонов, 6560 матчей; параметры подобраны с проверкой
   «обучение на 4 сезонах — проверка на пятом»): калибровка уверенности 1,33 (модель была слишком
   осторожна), добавка домашнему преимуществу 1,5%, бэк-ту-бэк 5%, тихоокеанские хозяева 3,5%, вратарь
   вдвое слабее (эффект на истории маленький), травмы −0,3/+0,4 гола на единицу xG, команды вне борьбы
   в конце сезона −3% (сильнее всего в годы «танкования»), первые 10 матчей нового тренера +5% (до
   смены команды играют на ~10 п.п. хуже модели, первые 10 матчей после — на ~10 п.п. лучше, дальше
   эффект исчезает; 24 смены 2021–2026). Тотал: p_over_blend = 60% рынка + 40% модели — модель на
   тоталах почти так же информативна, как линия, и вместе они точнее. Проверено и НЕ используется:
   сила по составу из личного xG игроков (хуже командной оценки), преемственность состава, отдых
   3+ дня и 3 матча за 4 дня, время начала, дополнительные признаки тотала.
   Итог против v3: угаданные исходы 64,1/61,1/61,7/60,1/55,1% против 63,1/61,6/60,0/59,4/55,3%,
   лог-лосс лучше во всех пяти сезонах (0,6596 против 0,6631), три исхода основного времени заметно
   точнее.
11. Плей-офф и нейтральные площадки. Плей-офф 2021–2026 (433 матча): та же модель угадывает ~57% (в
   регулярке ~60%), домашнее преимущество меньше, голов на 3% меньше — в плей-офф (id матча ..03....)
   без добавки хозяевам и λ × 0,97; это даёт 57,5% против 56,6%. Матчи на нейтральной площадке
   (upcoming[].neutral, Европа и т.п.) — без домашнего преимущества вовсе. Проверено и не используется:
   xG с поправкой на счёт/площадку/серии бросков вместо обычного (в пределах шума).
   Поле unmatched в model.json — игроки из травм и вратари, которых не удалось найти в данных
   (опечатки в именах): по ним модель поправку не делает.
12. Другие метрики команд. Проверены все осмысленные колонки MoneyPuck по командам на сегодня (Корси,
   Фенвик, доля бросков в створ, опасные/средние/неопасные моменты, добивания, вбрасывания, отборы и
   потери, хиты, удаления, блоки, реализация, % сейвов, PDO) — что добавляет к v4 при проверке «4 сезона —
   пятый». Устойчиво (лучше во всех 5 сезонах) одно сочетание: доля xG с неопасных позиций (+) вместе с
   Корси 5 на 5 (−) — команды, у которых «дальние» броски опаснее обычного при том же владении,
   выигрывают чаще, чем по общему xG. Слой: логит × 0,852 + 0,025 + 7,07 × Δдоли_неопасного_xG
   − 4,74 × ΔКорси (не больше ±0,4); лог-лосс −0,0015, угаданные +0,2 п.п. Входы: prior.json
   team_shares (прошлый сезон, вес 20 матчей) и data.team_xg ld_xgf/ld_xga/cf_5v5/ca_5v5.
   Опасные моменты, PDO, вбрасывания, хиты, удаления — ничего не добавляют.
   После этого слоя модель на закрывающих линиях 2021–2023 сравнялась с рынком (угаданные 64,2% против
   64,0%, лог-лосс 0,6430 против 0,6420), лучшая смесь — 60% рынка + 40% модели (MKT_W = 0,6).
   Ещё проверены и не используются: дивизионные матчи, форма по xG за 10 матчей, усталость вратаря
   (3+ старта за 7 дней, вчерашний матч), «ржавчина» после 5+ дней, медленный старт после глубокого
   плей-офф, «стиль на стиль» (владение × опасные моменты), реакция после разгрома, отдых лидеров
   в последних матчах, логит-смесь с рынком (нестабильна).
13. Вердикт и горизонт. Модель считает не только матчи дня (games), но и всё расписание недели вперёд
   (horizon, из data.week; бэк-ту-бэки — по расписанию; вратари там неизвестны). У каждого матча verdict:
   fav — кто вероятнее (по смеси с рынком, без кэфов — по модели); level: bet — перевес модели над рынком
   5+ п.п., либо «выгодный кэф» у российской конторы 5%+, либо усталость в пользу отдохнувших при перевесе
   2+ п.п.; lean — перевес 3–5 п.п. или выгодный кэф 3–5%; pass — кэф справедливый; noodds — кэфов ещё нет.
   bet — конкретная ставка (сторона с перевесом может быть и андердогом). total — сторона тотала по смеси.
14. Версия 4.2 (13.10.2026): модель и рынок разделены. Прогноз сайта (verdict.fav, verdict.total.side)
   берётся из чистой модели p_* / p_over, а не из смеси p_*_blend. Рынок пишется рядом: verdict.mkt_fav,
   verdict.total.mkt_side и флаги vs_market. Смесь p_*_blend по-прежнему считается — для сравнения и
   оценок «честной вероятности», но прогноз не определяет. Журнал хранит mkt_side, чтобы вести два
   счёта: модель и фаворит рынка, плюс отдельно матчи, где модель пошла против рынка.
15. Версия 4.3 (15.10.2026, по внешнему аудиту 14.10). Разбивка на основное время и ОТ согласована с итоговой
   вероятностью: шанс ничьей и доля хозяев в ОТ — как раньше, основное время подгоняется так, чтобы
   p_home_reg + p_ot × p_ot_home = p_home (раньше считалось до калибровки и расходилось на ~3 п.п., у 7% матчей
   разбивка показывала другого фаворита). Ничья у трёхисходных контор делится по доле побед в ОТ, а не пополам.
   Метка неполных данных: missing (чего не было) и incomplete (считали без xG команд, долей 5 на 5, вратаря
   или с ненайденным травмированным). Прогноз победителя и тотал не меняются. Бэктест scripts/backtest.py,
   6560 матчей 2021–2026: три исхода основного времени — лог-лосс 1,0369 → 1,0322 (лучше во всех 5 сезонах),
   фаворит в основное время: ждали 46,2% → 48,8%, было 48,4%.
"""
import json, math, sys, datetime
from collections import defaultdict

KEEP = 0.65        # доля прошлогоднего отличия от среднего
LAM = 30.0         # сила притяжения к прошлогоднему уровню (в «матчах»)
HALF = None        # без затухания: все матчи сезона весят одинаково (так точнее на истории)
XG_W = 0.7         # доля xG в цели
B2B = 0.95
SHARP = 1.33       # калибровка уверенности (подобрана на 5 сезонах, п. 10)
G_W = 0.25         # сила поправки на вратаря (v4: вдвое слабее, п. 10)
G_K = 200.0
PAC = 0.965        # поправка на домашние матчи тихоокеанских команд (п. 8)
PACIFIC = {"ANA", "LAK", "SEA", "SJS", "VAN", "VGK"}
MKT_W = 0.6        # вес рынка в итоговой вероятности p_*_blend (v4.1: модель догнала рынок, п. 12)        # «виртуальные» ожидаемые голы среднего уровня в оценке вратаря
OT_HOME = 0.517    # хозяева после ничьей в основное время (3 на 3 — 53,5%, буллиты — 50%)
OT_K = 0.45        # в овертайме сильнейший выигрывает чаще: + OT_K × (перевес в основное время)
TIE_K = 1.35       # ничьих в основное время в НХЛ на треть больше, чем у независимого Пуассона
HA_MULT = 1.015    # добавка домашнему преимуществу (рейтинги по xG его недооценивают)
OUT_F = 0.97       # команда вне борьбы за плей-офф в конце сезона
OUT_GAP = -0.08    # отставание по % очков от 16-го места в лиге
OUT_GP = 62        # с какого матча сезона
COACH_F = 1.05     # первые 10 матчей после смены главного тренера
COACH_N = 10
TOT_MKT_W = 0.6    # вес рынка в тотале p_over_blend
SH_LDX = 7.07      # слой «качество неопасных бросков» (п. 12): +7,07 × разница долей xG с неопасных позиций
SH_CF = -4.74      #   и −4,74 × разница Корси 5 на 5; логит модели × SH_L, + SH_C
SH_L = 0.852
SH_C = 0.025
SH_K = 20          # прошлый сезон весит как 20 матчей
PO_TOT = 0.97      # плей-офф: голов на 3% меньше, без добавки хозяевам (п. 11)
SV_K = 1000        # «виртуальные» броски среднего уровня в оценке вратаря
SV_LAST_W = 0.7    # вес бросков прошлого сезона
SV_ROOKIE = 0.890  # уровень вратаря без истории
VALUE_EDGE = 0.05
SOFT_EDGE = 0.03   # российская контора: кэф выше честного минимум на 3%
INJ_STATUSES = ("out", "ir", "ltir")
INJ_FOR = 0.3      # −голов своей команды на единицу личного xG за матч отсутствующего (п. 5)
INJ_AGAINST = 0.4  # +голов соперника на ту же единицу
INJ_MIN_RATE = 0.12  # нижний порог xG за матч для «ключевого»
TOP_N = 6          # ключевые = топ-6 своей команды по личному xG за матч
D_TOI_K = 0.012    # защитник из топ-4 по времени: ±голов за каждую минуту сверх D_TOI_BASE
D_TOI_BASE = 16.0
PRIOR_GP = 20      # прошлые сезоны весят не больше 20 матчей


def pois(k, l):
    return math.exp(-l) * l ** k / math.factorial(k)


def load(p):
    return json.load(open(p, encoding="utf-8"))


def ln(s):
    s = (s or "").split("(")[0].split("—")[0].strip()
    return s.split()[-1].lower() if s else ""


def fit(games, prior, today, prior_xg=None, txg=None):
    teams = sorted(prior)
    if prior_xg and all(t in prior_xg for t in teams):
        pa = {t: KEEP * prior_xg[t][0] for t in teams}; pd = {t: KEEP * prior_xg[t][1] for t in teams}
    else:
        lg = sum(v[5] for v in prior.values()) / sum(v[0] for v in prior.values())
        pa = {t: 0.4 * KEEP * math.log(prior[t][5] / prior[t][0] / lg) for t in teams}
        pd = {t: 0.4 * KEEP * math.log(prior[t][6] / prior[t][0] / lg) for t in teams}
    att, dfn = dict(pa), dict(pd)
    xf = xa = None
    if txg and len(txg) >= 30:
        xf = {t: v["xgf"] / max(v["gp"], 1) for t, v in txg.items() if v.get("gp")}
        xa = {t: v["xga"] / max(v["gp"], 1) for t, v in txg.items() if v.get("gp")}
    rows = []
    for g in games:
        hs, as_ = g["hs"], g["as"]
        if g.get("end") == "SO":
            if hs > as_: hs -= 1
            else: as_ -= 1
        h, a = g["home"], g["away"]
        if xf and h in xf and a in xf:
            hs = (1 - XG_W) * hs + XG_W * 0.5 * (xf[h] + xa[a])
            as_ = (1 - XG_W) * as_ + XG_W * 0.5 * (xf[a] + xa[h])
        age = (today - datetime.date.fromisoformat(g["date"])).days
        w = 0.5 ** (age / HALF) if HALF else 1.0
        rows.append((h, a, hs, as_, w))
    if not rows:
        return att, dfn, math.log(3.0), 0.04
    mu = math.log(sum(r[2] + r[3] for r in rows) / (2 * len(rows)))
    ha = 0.04
    for _ in range(25):
        for prm, pri, is_att in ((att, pa, True), (dfn, pd, False)):
            num = defaultdict(float); den = defaultdict(float)
            for h, a, hs, as_, w in rows:
                for side, opp, goals, s in ((h, a, hs, 1), (a, h, as_, -1)):
                    lam = math.exp(mu + att[side] + dfn[opp] + s * ha)
                    t = side if is_att else opp
                    num[t] += w * (goals - lam); den[t] += w * lam
            for t in teams:
                prm[t] += (num[t] - LAM * (prm[t] - pri[t])) / (den[t] + LAM)
        n = d = 0.0
        for h, a, hs, as_, w in rows:
            lh = math.exp(mu + att[h] + dfn[a] + ha); la = math.exp(mu + att[a] + dfn[h] - ha)
            n += w * ((hs - lh) - (as_ - la)); d += w * (lh + la)
        ha += n / (d + 200)
        tot = sum(w * (hs + as_) for h, a, hs, as_, w in rows); exp_ = sum(w * (math.exp(mu + att[h] + dfn[a] + ha) + math.exp(mu + att[a] + dfn[h] - ha)) for h, a, hs, as_, w in rows)
        mu += math.log(tot / exp_)
    return att, dfn, mu, ha


def split_reg(ph, tie, q):
    """v4.3: разбивка итоговой (после калибровки и слоя долей) вероятности на основное время и ОТ.
    Шанс ничьей tie — от Пуассона × TIE_K; доля хозяев после ничьей q — как подобрана на 1450 матчах
    (OT_HOME + OT_K × сырой перевес). Основное время подгоняется так, чтобы phr + tie × q = ph точно."""
    phr = min(1 - tie, max(0.0, ph - tie * q))
    return phr, 1 - tie - phr, q


def main(ap, dp, pp, gp_=None):
    A = load(ap); D = load(dp); PRF = load(pp); PR = PRF["teams"]; GP = load(gp_)["goalies"] if gp_ else PRF["goalies"]
    games = [g for g in A["games"] if g.get("as") is not None]
    up_day = D.get("upcoming_date") or datetime.date.today().isoformat()
    today = datetime.date.fromisoformat(up_day)
    att, dfn, mu, ha = fit(games, PR, today, PRF.get("teams_xg"), D.get("team_xg"))
    xg_ok = bool(D.get("team_xg")) and len(D.get("team_xg")) >= 30

    # --- вратари
    sv_lg = sum(v[1] * v[2] for v in GP.values()) / sum(v[1] for v in GP.values())
    cur = {}
    for g in D.get("goalies", []):
        cur[(g.get("team"), ln(g.get("name")))] = g
    gp_by_ln = {}
    for name, v in GP.items():
        gp_by_ln.setdefault(ln(name), []).append((name, v))

    def talent(team, label):
        l = ln(label)
        c = cur.get((team, l))
        last = None
        for name, v in gp_by_ln.get(l, []):
            last = v
        sa_c = (c.get("gp", 0) * 27) if c else 0
        sv_c = c.get("sv") if c and c.get("sv") else sv_lg
        base = sv_lg if (last and last[0] >= 20) else SV_ROOKIE
        num = base * SV_K + sv_c * sa_c; den = SV_K + sa_c
        if last:
            num += last[2] * last[1] * SV_LAST_W; den += last[1] * SV_LAST_W
        return num / den, (c or {}), last

    def team_mix(team):
        gs = [g for g in D.get("goalies", []) if g.get("team") == team and g.get("gp")]
        if not gs:
            return sv_lg
        tot = sum(g["gp"] for g in gs)
        return sum(talent(team, g["name"])[0] * g["gp"] for g in gs) / tot

    # --- вратари v3: сейвы сверх ожидаемого (GSAx) за прошлые сезоны + этот сезон
    GSX = PRF.get("goalies_gsax") or {}
    CUR = D.get("goalie_xg") or {}
    def nkey(s):
        return "".join(ch for ch in (s or "").split("(")[0].lower() if ch.isalpha())
    gsx_n = {nkey(k): v for k, v in GSX.items()}; cur_n = {nkey(k): v for k, v in CUR.items()}

    unmatched = {"goalies": [], "injuries": []}

    def gsax_factor(label):
        if not label:
            return 0.0, 1.0
        k = nkey(label)
        if k not in gsx_n and k not in cur_n and not any(nkey(g.get("name")) == k for g in D.get("goalies", [])):
            unmatched["goalies"].append(label.split("(")[0].strip())
        pg, px = (gsx_n.get(k) or [0.0, 0.0])
        c = cur_n.get(k) or {}
        cg = (c.get("xga") or 0) - (c.get("ga") or 0); cx = c.get("xga") or 0
        g = (pg + cg) / (px + cx + G_K)
        return g, max(0.9, min(1.1, 1 - G_W * g))

    # --- травмы
    sk = defaultdict(list)
    for s in D.get("skaters", []):
        sk[s["team"]].append(s)

    # --- травмы v3.2: ценность игрока = личный xG за матч (п. 5)
    PIX = {nkey(k): v for k, v in (PRF.get("players_ixg") or {}).items()}
    CIX = {nkey(k): v for k, v in (D.get("skater_xg") or {}).items()}

    def ixg_rate(name):
        k = nkey(name); pr = PIX.get(k); c = CIX.get(k)
        gp = xg = 0.0
        if pr:
            w = min(1.0, PRIOR_GP / max(pr[0], 1)); gp += w * pr[0]; xg += w * pr[1]
        if c and c.get("gp"):
            gp += c["gp"]; xg += c.get("ixg", 0.0)
        return (xg / gp, c.get("gp", 0) if c else 0) if gp >= 5 else (None, 0)

    def team_pool(team):
        """Игроки команды с ценностью: (имя, xG за матч, позиция, время на льду, игр в сезоне)."""
        pool = {}
        for p in sk[team]:
            r, g = ixg_rate(p["name"])
            if r is None and p.get("gp", 0) >= 5:
                r = 0.9 * p.get("pts", 0) / p["gp"] * 0.35
            pool[p["name"].lower()] = (p["name"], r or 0.0, p.get("pos"), p.get("toi"), p.get("gp", 0))
        for x in ((D.get("teams") or {}).get(team) or {}).get("injuries") or []:
            nm = x.get("name") or ""
            if nm.lower() not in pool:
                r, g = ixg_rate(nm)
                pool[nm.lower()] = (nm, r or 0.0, None, None, g)
        return pool

    def inj_unmatched(team):
        return any(x.endswith(f"({team})") for x in unmatched["injuries"])

    def injury_adj(team, base_for, base_against):
        out = []; d_for = d_against = 0.0
        pool = team_pool(team)
        top6 = {k for k, v in sorted(pool.items(), key=lambda kv: -kv[1][1])[:TOP_N] if v[1] >= INJ_MIN_RATE}
        dmen = sorted([(v[3], k) for k, v in pool.items() if v[2] == "D" and v[3] and v[4] >= 3], reverse=True)[:4]
        dtop = {k: t for t, k in dmen}
        team_gp = max([s.get("gp", 0) for s in sk[team]] or [0])
        inj = ((D.get("teams") or {}).get(team) or {}).get("injuries") or []
        for x in inj:
            st = (x.get("status") or "").lower()
            if not any(st == k or st.startswith(k) for k in INJ_STATUSES):
                continue
            key = (x.get("name") or "").lower()
            if key not in pool:
                continue
            is_goalie = nkey(pool[key][0]) in gsx_n or any(nkey(g.get("name")) == nkey(pool[key][0]) for g in D.get("goalies", []))
            if not is_goalie and pool[key][1] <= 0 and pool[key][4] == 0 and ixg_rate(pool[key][0])[0] is None:
                unmatched["injuries"].append(f'{pool[key][0]} ({team})')
            nm, rate, pos, toi, gp_cur = pool[key]
            fx = INJ_FOR * rate if key in top6 else 0.0
            ax = INJ_AGAINST * rate if key in top6 else 0.0
            fd = ad = 0.0
            if key in dtop:
                fd = ad = D_TOI_K * max(0.0, dtop[key] - D_TOI_BASE)
            f, a_ = max(fx, fd), max(ax, ad)
            if f <= 0 and a_ <= 0:
                continue
            k = 1.0 if (gp_cur > 0 or team_gp < 20) else 0.5   # давно не играет и команда уже привыкла
            f *= k; a_ *= k
            d_for += f; d_against += a_
            out.append(dict(name=nm, ixg_pg=round(rate, 3), toi=round(toi, 1) if toi else None,
                            basis="toi" if fd > fx else "xg",
                            d_for=round(f / base_for, 3), d_against=round(a_ / base_against, 3)))
        d_for = min(d_for, 0.6); d_against = min(d_against, 0.4)
        return d_for / base_for, d_against / base_against, out

    # --- доли команды: xG с неопасных позиций и Корси 5 на 5 (п. 12)
    TSH = PRF.get("team_shares") or {}
    def shares(t):
        pr = TSH.get(t); x = (D.get("team_xg") or {}).get(t) or {}
        num_l = den_l = num_c = den_c = 0.0
        if pr:
            num_l += SH_K * pr[0]; den_l += SH_K; num_c += SH_K * pr[1]; den_c += SH_K
        if x.get("ld_xgf") is not None and x.get("ld_xga") is not None and x.get("gp"):
            tot = x["ld_xgf"] + x["ld_xga"]
            if tot > 0: num_l += x["gp"] * x["ld_xgf"] / tot; den_l += x["gp"]
        if x.get("cf_5v5") is not None and x.get("ca_5v5") is not None and x.get("gp"):
            tot = x["cf_5v5"] + x["ca_5v5"]
            if tot > 0: num_c += x["gp"] * x["cf_5v5"] / tot; den_c += x["gp"]
        if not den_l or not den_c:
            return None
        return num_l / den_l, num_c / den_c

    last_played = defaultdict(set)
    for g in games:
        last_played[g["away"]].add(g["date"]); last_played[g["home"]].add(g["date"])
    for g in D.get("week", []):   # расписание вперёд — для бэк-ту-бэков в будущих днях
        if g.get("date") and g["date"] > (max((x["date"] for x in games), default="")):
            last_played[g["away"]].add(g["date"]); last_played[g["home"]].add(g["date"])

    # --- мотивация: вне борьбы за плей-офф в конце сезона (п. 10)
    st_rows = [x for x in D.get("standings", []) if x.get("gp")]
    ppct = {x["abbr"]: x["pts"] / (2 * x["gp"]) for x in st_rows}
    line16 = sorted(ppct.values(), reverse=True)[15] if len(ppct) >= 16 else None
    def out_of_race(t):
        x = next((y for y in st_rows if y["abbr"] == t), None)
        return bool(x and line16 is not None and x["gp"] >= OUT_GP and ppct[t] - line16 < OUT_GAP)

    # --- новый тренер: первые COACH_N матчей после смены (data.coach_changes = [{"team","date"}])
    def verdict(r, odds):
        """Вердикт модели (п. 13): кто вероятнее и есть ли ставка с перевесом."""
        fav = "home" if r["p_home"] >= 0.5 else "away"   # v4.2: прогноз — чистая модель, рынок отдельно
        v = dict(fav=fav, p_fav=r[f"p_{fav}"])
        if "mkt_home" in r:
            v["mkt_fav"] = "home" if r["mkt_home"] >= 0.5 else "away"; v["vs_market"] = v["mkt_fav"] != fav
        if "mkt_home" not in r:
            v.update(level="noodds"); return v
        es = "home" if r["edge_home"] >= r["edge_away"] else "away"; edge = r[f"edge_{es}"]
        fat = bool(r.get("fatigue_edge")) and ((r["b2b_away"] and es == "home") or (r["b2b_home"] and es == "away"))
        sb = r["soft"][0] if r.get("soft") else None
        level = "pass"
        if edge >= 0.05 or (sb and sb["ev"] >= 0.05) or (fat and edge >= 0.02):
            level = "bet"
        elif edge >= 0.03 or (sb and sb["ev"] >= 0.03):
            level = "lean"
        v.update(level=level, edge_side=es, edge=round(edge, 3), fatigue=fat)
        if level != "pass":
            if edge >= 0.03 or (fat and edge >= 0.02):
                v["bet"] = dict(kind="win", side=es, odds=odds.get(es), p_model=r[f"p_{es}"], p_mkt=r[f"mkt_{es}"], src=odds.get("source", "Pinnacle"))
            elif sb:
                v["bet"] = dict(kind="soft", **sb)
        if r.get("mkt_over") is not None:
            eo = r["edge_over"]; ts = "over" if r["p_over"] >= 0.5 else "under"; ms = "over" if r["mkt_over"] >= 0.5 else "under"
            v["total"] = dict(side=ts, line=r["line"], p=r["p_over"] if ts == "over" else r["p_under"], mkt_side=ms, vs_market=ms != ts,
                              value=("over" if eo >= VALUE_EDGE else "under" if -eo >= VALUE_EDGE else None))
        return v

    def new_coach(t):
        ch = [c["date"] for c in D.get("coach_changes", []) if c.get("team") == t and c.get("date")]
        if not ch:
            return False
        d0 = max(ch)
        n = sum(1 for g in games if t in (g["home"], g["away"]) and g["date"] >= d0)
        return n < COACH_N

    out = []; horizon = []
    up_keys = {(m["away"], m["home"]) for m in D.get("upcoming", [])}
    fut = [dict(w, horizon=True) for w in D.get("week", []) if w.get("date", "") > up_day and (w["away"], w["home"]) not in up_keys]
    for m in D.get("upcoming", []) + fut:
        a, h = m["away"], m["home"]
        day = m.get("date") or up_day
        prev = (datetime.date.fromisoformat(day) - datetime.timedelta(days=1)).isoformat()
        b2b_a = prev in last_played[a]; b2b_h = prev in last_played[h]
        gl = (m.get("goalies") or []) + [None, None]
        ta, ca, la_ = talent(a, gl[0]); th, ch, lh_ = talent(h, gl[1])
        mix_a, mix_h = team_mix(a), team_mix(h)
        ga_, fa = gsax_factor(gl[0])   # множитель к голам ПРОТИВ гостей
        gh_, fh = gsax_factor(gl[1])
        is_po = str(m.get("id", ""))[4:6] == "03"
        neutral = bool(m.get("neutral"))
        ha_g = 0.0 if neutral else ha
        bh_ = math.exp(mu + att[h] + dfn[a] + ha_g); ba_ = math.exp(mu + att[a] + dfn[h] - ha_g)
        ia, ja, inj_a = injury_adj(a, ba_, bh_); ih, jh, inj_h = injury_adj(h, bh_, ba_)
        lam_h = bh_ * fa * (1 - ih) * (1 + ja)
        lam_a = ba_ * fh * (1 - ia) * (1 + jh)
        if b2b_h and not b2b_a: lam_h *= B2B; lam_a /= B2B
        if b2b_a and not b2b_h: lam_a *= B2B; lam_h /= B2B
        pac = h in PACIFIC and not neutral
        if pac: lam_h *= PAC; lam_a /= PAC
        if not (is_po or neutral):
            lam_h *= HA_MULT; lam_a /= HA_MULT
        if is_po:
            lam_h *= PO_TOT; lam_a *= PO_TOT
        out_h, out_a = (False, False) if is_po else (out_of_race(h), out_of_race(a))
        if out_h: lam_h *= OUT_F; lam_a /= OUT_F
        if out_a: lam_a *= OUT_F; lam_h /= OUT_F
        nc_h, nc_a = (False, False) if is_po else (new_coach(h), new_coach(a))
        if nc_h: lam_h *= COACH_F; lam_a /= COACH_F
        if nc_a: lam_a *= COACH_F; lam_h /= COACH_F
        P = [[pois(i, lam_h) * pois(j, lam_a) for j in range(13)] for i in range(13)]
        phr0 = sum(P[i][j] for i in range(13) for j in range(13) if i > j)
        par0 = sum(P[i][j] for i in range(13) for j in range(13) if j > i)
        tie0 = 1 - phr0 - par0
        tie = min(0.5, tie0 * TIE_K); phr = phr0 * (1 - tie) / (phr0 + par0); par = par0 * (1 - tie) / (phr0 + par0)
        q_ot = min(0.8, max(0.2, (0.5 if neutral else OT_HOME) + OT_K * (phr - par)))
        ph = phr + tie * q_ot
        zz = SHARP * math.log(ph / (1 - ph))
        sh_h, sh_a = shares(h), shares(a); sh_adj = 0.0
        if sh_h and sh_a:
            sh_adj = max(-0.4, min(0.4, SH_C + SH_LDX * (sh_h[0] - sh_a[0]) + SH_CF * (sh_h[1] - sh_a[1]) + (SH_L - 1) * zz))
        ph = 1 / (1 + math.exp(-(zz + sh_adj))); pa = 1 - ph
        phr_raw, q_raw = phr, q_ot
        phr, par, q_ot = split_reg(ph, tie, q_ot)   # v4.3: разбивка согласована с итоговой p_home
        odds = m.get("odds") or {}; fon = m.get("fonbet") or {}
        line = fon.get("total") or odds.get("total") or 5.5
        p_over = sum(P[i][j] for i in range(13) for j in range(13) if i + j + (1 if i == j else 0) > line)
        if float(line).is_integer():  # целая линия: ровно line голов — возврат, считаем без него
            p_push = sum(P[i][j] for i in range(13) for j in range(13) if i + j + (1 if i == j else 0) == line)
            p_over = p_over / max(1e-9, 1 - p_push)
        r = dict(away=a, home=h, lam_away=round(lam_a, 2), lam_home=round(lam_h, 2),
                 p_home=round(ph, 3), p_away=round(pa, 3), p_ot=round(tie, 3),
                 p_home_reg=round(phr, 3), p_away_reg=round(par, 3),
                 exp_total=round(lam_h + lam_a + tie0, 2), line=line,
                 p_over=round(p_over, 3), p_under=round(1 - p_over, 3),
                 fair_home=round(1 / ph, 2), fair_away=round(1 / pa, 2),
                 b2b_away=b2b_a, b2b_home=b2b_h, pacific_home=pac, playoff=is_po, neutral=neutral, out_home=out_h, out_away=out_a, new_coach_home=nc_h, new_coach_away=nc_a, p_ot_home=round(q_ot, 3), shares_home=[round(v, 3) for v in sh_h] if sh_h else None, shares_away=[round(v, 3) for v in sh_a] if sh_a else None, shares_adj=round(sh_adj, 3),
                 goalie_away=dict(name=gl[0], gsax_rate=round(ga_, 4), talent=round(ta, 4), team_level=round(mix_a, 4), factor=round(fa, 3), sv=ca.get("sv"), gp=ca.get("gp"), last=la_),
                 goalie_home=dict(name=gl[1], gsax_rate=round(gh_, 4), talent=round(th, 4), team_level=round(mix_h, 4), factor=round(fh, 3), sv=ch.get("sv"), gp=ch.get("gp"), last=lh_),
                 inj_away=inj_a, inj_home=inj_h, inj_adj_away=round(ia, 3), inj_adj_home=round(ih, 3), inj_def_away=round(ja, 3), inj_def_home=round(jh, 3),
                 rating_away=dict(att=round(math.exp(att[a]), 3), dfn=round(math.exp(dfn[a]), 3)),
                 rating_home=dict(att=round(math.exp(att[h]), 3), dfn=round(math.exp(dfn[h]), 3)))
        # рынок для сравнения: Pinnacle (самая точная линия), если нет — Фонбет
        mh = odds.get("home") or fon.get("home"); ma = odds.get("away") or fon.get("away")
        if mh and ma:
            ih_, ia_ = 1 / mh, 1 / ma
            r["mkt_home"] = round(ih_ / (ih_ + ia_), 3); r["mkt_away"] = round(ia_ / (ih_ + ia_), 3)
            r["edge_home"] = round(ph - r["mkt_home"], 3); r["edge_away"] = round(pa - r["mkt_away"], 3)
            r["p_home_blend"] = round(MKT_W * r["mkt_home"] + (1 - MKT_W) * ph, 3); r["p_away_blend"] = round(1 - r["p_home_blend"], 3)
            r["fatigue_edge"] = (b2b_a != b2b_h)
            best = max((r["edge_home"], "home"), (r["edge_away"], "away"))
            r["value"] = best[1] if best[0] >= VALUE_EDGE else None
        mo = (odds.get("over") if odds.get("total") == line else None) or fon.get("over")
        mu_ = (odds.get("under") if odds.get("total") == line else None) or fon.get("under")
        if mo and mu_:
            io, iu = 1 / mo, 1 / mu_
            r["mkt_over"] = round(io / (io + iu), 3); r["edge_over"] = round(p_over - r["mkt_over"], 3)
            r["p_over_blend"] = round(TOT_MKT_W * r["mkt_over"] + (1 - TOT_MKT_W) * p_over, 3); r["p_under_blend"] = round(1 - r["p_over_blend"], 3)
            r["value_total"] = "over" if r["edge_over"] >= VALUE_EDGE else "under" if -r["edge_over"] >= VALUE_EDGE else None
        # --- российские/«мягкие» конторы: где кэф выше честного (п. 9)
        def pover_at(L):
            v = sum(P[i][j] for i in range(13) for j in range(13) if i + j + (1 if i == j else 0) > L)
            if float(L).is_integer():
                pp = sum(P[i][j] for i in range(13) for j in range(13) if i + j + (1 if i == j else 0) == L)
                v = v / max(1e-9, 1 - pp)
            return v
        fair_h = r.get("p_home_blend", ph); fair_a = 1 - fair_h
        def fair_over(L):
            if r.get("mkt_over") is not None and odds.get("total") is not None:
                base = TOT_MKT_W * r["mkt_over"] + (1 - TOT_MKT_W) * pover_at(odds["total"])
                return min(0.97, max(0.03, base + pover_at(L) - pover_at(odds["total"])))
            return pover_at(L)
        soft = []
        def add(book, bet, o, fp):
            if o and fp and o > 1:
                ev = o * fp - 1
                if ev >= SOFT_EDGE:
                    soft.append(dict(book=book, bet=bet, odds=round(o, 2), fair=round(1 / fp, 2), ev=round(ev, 3)))
        x1 = m.get("odds_1x") or {}
        if x1.get("home") and x1.get("draw") and x1.get("away"):
            S = 1 / x1["home"] + 1 / x1["draw"] + 1 / x1["away"]; dr = (1 / x1["draw"]) / S
            add("1xBet", f"П1 {h} (осн. время)", x1["home"], max(0.01, fair_h - q_ot * dr))
            add("1xBet", f"П2 {a} (осн. время)", x1["away"], max(0.01, fair_a - (1 - q_ot) * dr))
        books = dict(m.get("books") or {})
        for bk, bo in books.items():
            nm_ = {"marathonbet": "Марафон", "onexbet": "1xBet"}.get(bk, bk)
            if bo.get("home") and bo.get("away") and not bo.get("draw"):
                add(nm_, f"{h} (с ОТ)", bo["home"], fair_h); add(nm_, f"{a} (с ОТ)", bo["away"], fair_a)
            elif bo.get("home") and bo.get("away") and bo.get("draw"):
                S3 = 1 / bo["home"] + 1 / bo["draw"] + 1 / bo["away"]; dr3 = (1 / bo["draw"]) / S3
                add(nm_, f"П1 {h} (осн. время)", bo["home"], max(0.01, fair_h - q_ot * dr3))
                add(nm_, f"П2 {a} (осн. время)", bo["away"], max(0.01, fair_a - (1 - q_ot) * dr3))
        for nm_, bo in [("1xBet", x1)] + [({"marathonbet": "Марафон"}.get(k, k), v) for k, v in books.items()]:
            if bo.get("total") is not None and bo.get("over") and bo.get("under"):
                L = bo["total"]; fo = fair_over(L)
                if bo.get("draw"):
                    # трёхисходная контора (1xBet, Марафон): тотал тоже основного времени — гол в ОТ/буллитах
                    # не считается. Разница только когда ничья с суммой floor(L) (3:3 при 6,5): вычитаем её шанс.
                    if float(L).is_integer():
                        continue
                    n = int(math.floor(L))
                    fo = max(0.03, fo - TIE_K * sum(P[i][i] for i in range(13) if 2 * i == n))
                add(nm_, f"ТБ {bo['total']}", bo["over"], fo); add(nm_, f"ТМ {bo['total']}", bo["under"], 1 - fo)
        r["soft"] = sorted(soft, key=lambda z: -z["ev"])
        r["h2h"] = [dict(date=g["date"], away=g["away"], home=g["home"], score=f'{g["as"]}:{g["hs"]}', end=g.get("end"))
                    for g in games if {g["away"], g["home"]} == {a, h}]
        r.update(id=m.get("id"), date=day, start=m.get("start"))
        r["p_home_reg_raw"] = round(phr_raw, 3); r["p_ot_home_raw"] = round(q_raw, 3)   # до согласования — для бэктеста
        miss = []
        if not xg_ok: miss.append("xg")             # нет командного xG MoneyPuck — сила только по голам
        if not (sh_h and sh_a): miss.append("shares")
        for side, nm_g in (("away", gl[0]), ("home", gl[1])):
            if not nm_g: miss.append(f"goalie_{side}")
            elif nkey(nm_g) not in gsx_n and nkey(nm_g) not in cur_n: miss.append(f"goalie_{side}_unknown")
            elif "не подтв" in nm_g: miss.append(f"goalie_{side}_unconfirmed")
        if inj_unmatched(a) or inj_unmatched(h): miss.append("injuries_unmatched")
        if "mkt_home" not in r: miss.append("odds")
        r["missing"] = miss
        # «неполные данные»: модель считала без существенного входа; неподтверждённый вратарь и отсутствие кэфов — не в счёт
        r["incomplete"] = any(x in ("xg", "shares", "goalie_away", "goalie_home", "injuries_unmatched") or x.endswith("_unknown") for x in miss)
        r["verdict"] = verdict(r, odds)
        (horizon if m.get("horizon") else out).append(r)

    T = defaultdict(lambda: dict(gp=0, gf=0, ga=0, sf=0, sa=0, sgp=0, ppg=0, ppga=0))
    for g in games:
        for side, gf, ga, i in ((g["away"], g["as"], g["hs"], 0), (g["home"], g["hs"], g["as"], 1)):
            t = T[side]; t["gp"] += 1; t["gf"] += gf; t["ga"] += ga
            if g.get("sog"): t["sf"] += g["sog"][i]; t["sa"] += g["sog"][1 - i]; t["sgp"] += 1
            for x in g.get("goals", []):
                if x[2] == "pp":
                    if x[1] == side: t["ppg"] += 1
                    else: t["ppga"] += 1
    teams = {}
    for k in att:
        t = T[k]; gpn = max(t["gp"], 1)
        teams[k] = dict(gp=t["gp"], gf_pg=round(t["gf"] / gpn, 2), ga_pg=round(t["ga"] / gpn, 2),
                        sf_pg=round(t["sf"] / max(t["sgp"], 1), 1), sa_pg=round(t["sa"] / max(t["sgp"], 1), 1),
                        ppg=t["ppg"], ppga=t["ppga"], att=round(math.exp(att[k]), 3), dfn=round(math.exp(dfn[k]), 3),
                        power=round(math.exp(att[k] - dfn[k]), 3))
    json.dump(dict(version=4.3, xg_used=bool(D.get("team_xg")), generated=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                   league=dict(goals_pg=round(math.exp(mu), 3), home_adv=round(math.exp(ha) ** 2 - 1, 3), sv=round(sv_lg, 4), games=len(games)),
                   backtest=dict(seasons="2021-22…2025-26", games=6560, accuracy_v4=[0.641, 0.611, 0.617, 0.601, 0.551], accuracy_v3=[0.631, 0.616, 0.600, 0.594, 0.553], logloss_v4=0.6596, logloss_v3=0.6631),
                   games=out, horizon=horizon, teams=teams, unmatched={k: sorted(set(v)) for k, v in unmatched.items()}), sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:5])
