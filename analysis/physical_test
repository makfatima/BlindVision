"""Analyse the three pre-submission physical-test CSVs.

Run from anywhere:  python3 analysis/analyze_physical_tests.py
Only filled rows are analysed; the report states how many planned rows are
still empty, so an incomplete test can never look complete."""
import csv, math, statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def load(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summ(xs):
    if not xs:
        return "n=0"
    sd = st.stdev(xs) if len(xs) > 1 else float("nan")
    return f"n={len(xs)} mean={st.mean(xs):.1f} median={st.median(xs):.1f} SD={sd:.1f} max={max(xs):.1f}"


def ultrasonic():
    rows = load(RES / "ultrasonic/ultrasonic_data_log.csv")
    done = [r for r in rows if r["measured_distance_cm"].strip() or r["no_echo"].strip() == "1"]
    print(f"\n== Ultrasonic: {len(done)}/{len(rows)} planned readings recorded")
    g, noecho, total = defaultdict(list), defaultdict(int), defaultdict(int)
    flags = defaultdict(lambda: [0, 0])
    for r in done:
        keys = [(r["matrix_type"], r["sensor"]),
                (r["matrix_type"], r["sensor"], r["firing_mode"]) if r["matrix_type"] == "CrossTalk" else None]
        keys = [k for k in keys if k]
        for k in keys:
            total[k] += 1
        if r["matrix_type"] == "Downward" and r["dropoff_flag"].strip():
            fk = (r["surface_type"], r["edge_state"])
            flags[fk][0] += int(r["dropoff_flag"]); flags[fk][1] += 1
        if r["no_echo"].strip() == "1" or not r["measured_distance_cm"].strip():
            for k in keys: noecho[k] += 1
            continue
        if not r["ground_truth_cm"].strip():
            continue
        e = float(r["measured_distance_cm"]) - float(r["ground_truth_cm"])
        for k in keys: g[k].append(e)
    for k in sorted(total):
        es = g[k]
        if es:
            n = len(es); bias = sum(es) / n
            mae = sum(abs(e) for e in es) / n
            rmse = math.sqrt(sum(e * e for e in es) / n)
            sd = st.stdev(es) if n > 1 else float("nan")
            worst = max(abs(e) for e in es)
            out = 100 * sum(abs(e) > 10 for e in es) / n
            m = f"bias={bias:+.2f} MAE={mae:.2f} RMSE={rmse:.2f} SD={sd:.2f} worst={worst:.2f} >10cm={out:.1f}%"
        else:
            m = "no valid readings"
        print(f"  {' / '.join(k):45s} valid={len(es)} no-echo={noecho[k]}/{total[k]}  {m}")
    for k, (hit, n) in sorted(flags.items()):
        print(f"  Drop-off flag {k[0]:9s} {k[1]:13s} raised {hit}/{n}")


def vision():
    rows = load(RES / "vision_only/vision_only_trials_log.csv")
    done = [r for r in rows if r["outcome"].strip()]
    print(f"\n== Vision-Only: {len(done)}/{len(rows)} planned trials recorded")
    for cam in ["Front", "Right", "Rear", "Left"]:
        rs = [r for r in done if r["camera_channel"] == cam]
        ok = sum(r["outcome"].strip() == "correct" for r in rs)
        lat = [float(r["latency_ms"]) for r in rs if r["latency_ms"].strip()]
        fails = defaultdict(int)
        for r in rs:
            if r["outcome"].strip() != "correct": fails[r["outcome"].strip()] += 1
        print(f"  {cam:5s} correct {ok}/{len(rs)}  latency {summ(lat)}  failures {dict(fails)}")


def haptic():
    rows = load(RES / "haptic_sos/haptic_sos_trials_log.csv")
    ms = lambda r, a, b: (float(r[b]) - float(r[a])) * 1000 / float(r["video_fps"])
    has = lambda r, *c: all(r[x].strip() for x in c)
    A = [r for r in rows if r["test_part"] == "PartA" and r["haptic_before_speech"].strip()]
    B = [r for r in rows if r["test_part"] == "PartB" and r["speech_interrupted"].strip()]
    print(f"\n== Haptic Part A: {len(A)}/15 trials recorded; haptic before speech "
          f"{sum(r['haptic_before_speech'] == '1' for r in A)}/{len(A)}")
    gap = [ms(r, "frame_haptic_onset", "frame_speech_onset") for r in A
           if has(r, "video_fps", "frame_haptic_onset", "frame_speech_onset")]
    trig = [ms(r, "frame_trigger", "frame_haptic_onset") for r in A
            if has(r, "video_fps", "frame_trigger", "frame_haptic_onset")]
    print(f"  speech onset - motor onset (ms): {summ(gap)}")
    print(f"  trigger - motor onset (ms):      {summ(trig)}")
    print(f"== SOS Part B: {len(B)}/15 trials recorded; speech interrupted "
          f"{sum(r['speech_interrupted'] == '1' for r in B)}/{len(B)}; SOS haptic observed "
          f"{sum(r['sos_haptic_observed'] == '1' for r in B)}/{len(B)}")
    stop = [ms(r, "frame_trigger", "frame_speech_stop") for r in B
            if has(r, "video_fps", "frame_trigger", "frame_speech_stop")]
    sos = [ms(r, "frame_trigger", "frame_sos_speech_onset") for r in B
           if has(r, "video_fps", "frame_trigger", "frame_sos_speech_onset")]
    print(f"  press - speech stop (ms):        {summ(stop)}")
    print(f"  press - SOS speech onset (ms):   {summ(sos)}")


if __name__ == "__main__":
    ultrasonic(); vision(); haptic()
