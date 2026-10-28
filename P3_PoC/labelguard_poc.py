#!/usr/bin/env python3
"""LabelGuard PoC  (Team Titans, P-2026-29-CD-003-AY26-27)  -- labelguard_poc.py

Usage:
  python labelguard_poc.py run1 v0.1            # seed 20261028, v0.1
  python labelguard_poc.py run2 v0.2            # same 30 labels, v0.2
  python labelguard_poc.py run3 v0.2 7777       # 30 fresh labels, v0.2

Components: label images = MOCKED (script-generated); Tesseract OCR (psm 6) = REUSED;
rule check v0.1 / v0.2 = BUILT. No OCR tuning. Synthetic data only.

v0.1: keyword not found -> ABSENT.
v0.2: same, but ABSENT -> UNCERTAIN if a value pattern for that field appears anywhere
      in the OCR text (safety net against silent misses). Thresholds unchanged.
"""
import csv, json, os, random, re, statistics, subprocess, sys, time, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FIELDS = ["NAME", "QTY", "MRP", "MFR", "DATE", "CARE", "ORIGIN"]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CONF_MIN = 55  # word-confidence floor for a value to count as readable

# ----------------------------------------------------------------- label generator (MOCKED)
KEYWORDS = {
    "NAME": ["Product Name", "Name of Commodity"],
    "QTY": ["Net Qty", "Net Quantity", "Net Wt."],
    "MRP": ["MRP", "Maximum Retail Price"],
    "MFR": ["Mfd. & Packed by", "Manufactured by", "Marketed by"],
    "DATE": ["Mfg Date", "Packed on", "Date of Manufacture"],
    "CARE": ["Customer Care", "Consumer Care"],
    "ORIGIN": ["Country of Origin", "Made in"],
}
PRODUCTS = ["Masala Peanut Chikki", "Herbal Face Wash", "Rose Body Lotion", "Ragi Cookies",
            "Tomato Ketchup", "Coconut Hair Oil", "Instant Noodles", "Neem Soap", "Mango Pickle",
            "Choco Wafer Biscuit", "Aloe Vera Gel", "Sambar Powder"]
FIRMS = ["Sunrise Foods Pvt Ltd", "Kovai Naturals Ltd", "GreenLeaf Industries", "Annam Foods Pvt Ltd"]


def make_truth(rng):
    qty = f"{rng.choice([50,100,150,200,250,500])} {rng.choice(['g','ml'])}"
    mrp = f"Rs. {rng.randint(10, 480)}.00"
    date = f"{rng.randint(1,28):02d}/{rng.randint(1,12):02d}/2026"
    phone = f"1800-{rng.randint(100,999)}-{rng.randint(1000,9999)}"
    vals = {
        "NAME": rng.choice(PRODUCTS),
        "QTY": qty,
        "MRP": mrp + " (incl. of all taxes)",
        "MFR": f"{rng.choice(FIRMS)}, {rng.randint(2,90)} Mill Rd, Coimbatore",
        "DATE": date,
        "CARE": phone,
        "ORIGIN": "India",
    }
    present = {f: (rng.random() > 0.15) for f in FIELDS}  # ~15% of fields genuinely absent
    return vals, present


def render_label(rng, vals, present, degraded):
    W, H = 1000, 760
    img = Image.new("RGB", (W, H), (252, 250, 244))
    d = ImageDraw.Draw(img)
    d.rectangle([14, 14, W - 15, H - 15], outline=(40, 40, 40), width=4)
    d.text((40, 34), "NATURE'S PICK", font=ImageFont.truetype(FONT_B, 40), fill=(20, 90, 40))
    d.text((40, 90), "Best before 6 months from packing. Store in a cool, dry place.",
           font=ImageFont.truetype(FONT, 20), fill=(60, 60, 60))
    size = 20 if (degraded and rng.random() < 0.5) else 28
    font = ImageFont.truetype(FONT, size)
    y = 150
    kws = {}
    for f in FIELDS:
        kw = rng.choice(KEYWORDS[f])
        kws[f] = kw
        if present[f]:
            d.text((40, y), f"{kw}: {vals[f]}", font=font, fill=(15, 15, 15))
        y += int(size * 2.1)
    d.text((40, H - 70), "Veg  |  FSSAI Lic. No. 12345678901234", font=ImageFont.truetype(FONT, 20), fill=(60, 60, 60))
    mode = None
    if degraded:
        mode = rng.choice(["rotate", "blur", "lowcontrast", "smallfont+blur"])
        if mode == "rotate":
            img = img.rotate(rng.choice([-1, 1]) * rng.uniform(3, 6), resample=Image.BICUBIC, fillcolor=(252, 250, 244))
        if mode in ("blur", "smallfont+blur"):
            img = img.filter(ImageFilter.GaussianBlur(rng.uniform(1.3, 2.2)))
        if mode == "lowcontrast":
            img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.30, 0.45))
    return img, kws, mode


def make_dataset(seed, n=30, n_degraded=10):
    rng = random.Random(seed)
    deg_ids = set(rng.sample(range(n), n_degraded))
    items = []
    for i in range(n):
        vals, present = make_truth(rng)
        img, kws, mode = render_label(rng, vals, present, i in deg_ids)
        items.append(dict(id=f"L{i+1:02d}", img=img, vals=vals, present=present, kws=kws,
                          degraded=i in deg_ids, mode=mode))
    return items


# ----------------------------------------------------------------- OCR (REUSED: Tesseract psm 6)
def ocr_lines(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    p = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6", "tsv"],
                       input=buf.getvalue(), capture_output=True, check=True)
    rows = p.stdout.decode("utf8", "ignore").splitlines()[1:]
    lines = {}
    for r in rows:
        c = r.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        key = (c[2], c[3], c[4])
        lines.setdefault(key, []).append((c[11], float(c[10]), int(c[6]), int(c[7]), int(c[8]), int(c[9])))
    out = []
    for k in sorted(lines, key=lambda k: tuple(int(x) for x in k)):
        out.append(lines[k])
    return out  # list of lines, each list of (word, conf, x, y, w, h)


# ----------------------------------------------------------------- rule check (BUILT)
KW_RE = {
    "NAME": r"product\s*name|name\s*of\s*commodity",
    "QTY": r"net\s*(qty|quantity|wt)",
    "MRP": r"\bm\.?r\.?p\b|maximum\s*retail\s*price",
    "MFR": r"(manufactured|marketed|packed|mfd\.?)[^:]{0,14}\bby\b",
    "DATE": r"(mfg|packed)\s*(date|on)|date\s*of\s*manufacture",
    "CARE": r"(customer|consumer)\s*care",
    "ORIGIN": r"country\s*of\s*origin|made\s*in",
}
VAL_RE = {
    "NAME": r"[A-Za-z]{3,}",
    "QTY": r"\d+\s*(g|gm|kg|ml|l)\b",
    "MRP": r"(rs\.?|₹)\s*\d+",
    "MFR": r"(pvt|ltd|limited|industries)\b",
    "DATE": r"\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{4}",
    "CARE": r"\d{4}[- ]?\d{3}[- ]?\d{4}",
    "ORIGIN": r"india|china|nepal|vietnam|thailand",
}
LABELS_NORM = lambda s: re.sub(r"\D", "", s) if s else ""


def check_field(field, lines, version):
    """returns (status, extracted, reason). status in PRESENT / ABSENT / UNCERTAIN"""
    kre = re.compile(KW_RE[field], re.I)
    vre = re.compile(VAL_RE[field], re.I)
    for ln in lines:
        text = " ".join(w[0] for w in ln)
        m = kre.search(text)
        if not m:
            continue
        rest = text[m.end():]
        vm = vre.search(rest)
        if not vm:
            return "UNCERTAIN", None, "keyword found, value unreadable"
        tail_words = [w for w in ln if w[0] and w[0] in rest]
        if tail_words and min(w[1] for w in tail_words) < CONF_MIN:
            return "UNCERTAIN", vm.group(0), "low OCR confidence"
        return "PRESENT", vm.group(0), "keyword + value"
    # keyword never found
    if version == "v0.2":
        full = " ".join(" ".join(w[0] for w in ln) for ln in lines)
        if field == "NAME":
            if re.search(r"name|commodity", full, re.I):
                return "UNCERTAIN", None, "value pattern seen without keyword"
        elif vre.search(full):
            return "UNCERTAIN", None, "value pattern seen without keyword"
    return "ABSENT", None, "keyword not found"


def score(item, field, status, extracted):
    truth_present = item["present"][field]
    if status == "UNCERTAIN":
        return "uncertain"
    if status == "ABSENT":
        return "correct" if not truth_present else "wrong"
    # PRESENT
    if not truth_present:
        return "wrong"
    if field in ("QTY", "MRP", "DATE", "CARE"):
        return "correct" if LABELS_NORM(extracted).startswith(LABELS_NORM(item["vals"][field])[:len(LABELS_NORM(extracted))]) and LABELS_NORM(extracted) else "wrong"
    return "correct"


def run(run_id, version, seed):
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, f"labels_{seed}"), exist_ok=True)
    items = make_dataset(seed)
    rows, per_label_time, silent_labels = [], [], []
    correct = 0
    uncertain = 0
    print(f"[{run_id}] labelguard_poc.py {version}  seed={seed}  labels={len(items)}  fields/label=7  tesseract psm 6", flush=True)
    for it in items:
        it["img"].save(os.path.join(OUT, f"labels_{seed}", f"{it['id']}.png"))
        t0 = time.perf_counter()
        lines = ocr_lines(it["img"])
        res = {f: check_field(f, lines, version) for f in FIELDS}
        dt = time.perf_counter() - t0
        per_label_time.append(dt)
        n_ok = 0
        silent = False
        marks = []
        for f in FIELDS:
            status, ext, why = res[f]
            sc = score(it, f, status, ext)
            if sc == "correct":
                correct += 1; n_ok += 1
            elif sc == "uncertain":
                uncertain += 1
            else:
                silent = True
            marks.append({"correct": "ok", "uncertain": "??", "wrong": "XX"}[sc])
            rows.append(dict(run=run_id, version=version, seed=seed, label=it["id"], degraded=int(it["degraded"]),
                             degrade_mode=it["mode"] or "", field=f, truth_present=int(it["present"][f]),
                             truth_value=it["vals"][f] if it["present"][f] else "", status=status,
                             extracted=ext or "", outcome=sc, reason=why, secs=round(dt, 3)))
        if silent:
            silent_labels.append(it["id"])
        tag = "DEG " if it["degraded"] else "CLEAN"
        flag = "  <-- SILENT WRONG RESULT" if silent else ""
        print(f"{it['id']} {tag} {' '.join(marks)}  {n_ok}/7 ok  {dt:5.2f}s{flag}", flush=True)
    n_checks = len(items) * len(FIELDS)
    summary = dict(run=run_id, version=version, seed=seed, labels=len(items), checks=n_checks,
                   T1_correct=correct, T1_pct=round(100 * correct / n_checks, 1), T1_pass=correct >= 189,
                   uncertain_fields=uncertain,
                   T2_silent_labels=len(silent_labels), T2_ids=silent_labels, T2_pass=len(silent_labels) == 0,
                   T3_median_s=round(statistics.median(per_label_time), 2), T3_pass=statistics.median(per_label_time) <= 10,
                   manual_comparator="Not tested")
    print(f"[{run_id}] T1 {correct}/{n_checks} ({summary['T1_pct']}%)  [{'PASS' if summary['T1_pass'] else 'FAIL'} >=189]   "
          f"UNCERTAIN fields {uncertain}", flush=True)
    print(f"[{run_id}] T2 silent-wrong labels {len(silent_labels)}/30 {silent_labels}  [{'PASS' if summary['T2_pass'] else 'FAIL'} =0]", flush=True)
    print(f"[{run_id}] T3 median {summary['T3_median_s']} s/label  [{'PASS' if summary['T3_pass'] else 'FAIL'} <=10 s]   manual comparator: Not tested", flush=True)
    with open(os.path.join(OUT, f"results_{run_id}_{version}_seed{seed}.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT, f"summary_{run_id}.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    return summary


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    run(a[0], a[1], int(a[2]) if len(a) > 2 else 20261028)
