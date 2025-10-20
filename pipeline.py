import re
import pandas as pd

# ---------- yardımcı: pykap varsa tickers al, yoksa fallback örnek
def get_bist_tickers():
    try:
        from pykap.bist_company_list import bist_company_list
        return bist_company_list()
    except Exception:
        return ["AVISA", "THYAO", "GARAN", "SASA", "AHGAZ"]

# ---------- sayı parse etme
def parse_number(num_str):
    s = num_str.strip().replace(" ", "")
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(',', '.')
        if s.count('.') > 1:
            s = s.replace('.', '')
    try:
        if '.' in s:
            return float(s)
        else:
            return int(s)
    except:
        digits = re.sub(r'[^\d]', '', s)
        return int(digits) if digits else 1

# ---------- miktar ve birim çıkarımı
def extract_amounts(text, units):
    pattern = r'(?P<num>\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?|\d+)\s*(?P<unit>' + '|'.join(map(re.escape, units)) + r')\b'
    matches = []
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        num = parse_number(m.group('num'))
        unit = m.group('unit').lower()
        matches.append({"num": num, "unit": unit, "start": m.start(), "end": m.end(), "text": m.group(0)})
    perc_pattern = r'(?P<pct>[-+]?\d+(?:[.,]\d+)?)\s*%'
    for m in re.finditer(perc_pattern, text, flags=re.IGNORECASE):
        num = parse_number(m.group('pct'))
        matches.append({"num": num, "unit": "%", "start": m.start(), "end": m.end(), "text": m.group(0)})
    return sorted(matches, key=lambda x: x['start'])

# ---------- hisse ticker tespiti
def find_tickers(text, tickers):
    found = []
    tickers_sorted = sorted(set(tickers), key=lambda x: -len(x))
    for t in tickers_sorted:
        pattern = r'(?<!\w)' + re.escape(t) + r'(?!\w)'
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.append({"ticker": t, "start": m.start(), "end": m.end(), "match": m.group(0)})
    return found

# ---------- action tespiti
BUY_WORDS = ["al", "aldım", "alındı", "almayı", "almak", "alıyorum", "alacak", "alınacak", "alırım", "alacağım"]
SELL_WORDS = ["sat", "sattı", "sattım", "satıldı", "satıyorum", "satılacak", "satılmak", "satacağım"]

def detect_action(text):
    low = text.lower()
    if any(re.search(r'\b' + re.escape(w) + r'\b', low) for w in BUY_WORDS):
        return "buy"
    if any(re.search(r'\b' + re.escape(w) + r'\b', low) for w in SELL_WORDS):
        return "sell"
    return None

# ---------- improved sentiment
def improved_rule_sentiment(text):
    t = text.lower()
    # negatif kelime + yok → neutral
    if any(kw in t for kw in ["negatif", "düşüş", "zarar"]) and "yok" in t:
        return "neutral"
    POS = ["iyi", "kazanç", "kazandım", "kâr", "kârlı", "pozitif", "mutlu", "harika", "yükseldi", "yükseliş", "arttı",
           "kârda"]
    NEG = ["düşüş","düştü","zarar","negatif","kötü","azaldı","kaybettim","problem","sıkıntı","eksilerde"]
    p = sum(t.count(w) for w in POS)
    n = sum(t.count(w) for w in NEG)
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"

# ---------- main analyze
def analyze_texts(texts, tickers=None, sentiment_analyzer=None, units=None, proximity_chars=60):
    if units is None:
        units = ["hisse","hissesi","adet","tane","lot","pay","birim","payı","paylar","lotu","lotlar","lotları"]
    if tickers is None:
        tickers = get_bist_tickers()

    results = []
    for text in texts:
        amount_matches = extract_amounts(text, units)
        ticker_matches = find_tickers(text, tickers)
        action = detect_action(text)

        # sentiment
        if sentiment_analyzer is not None:
            try:
                out = sentiment_analyzer(text)
                if isinstance(out, list) and len(out) > 0:
                    sentiment = out[0]['label'].lower()
                else:
                    sentiment = improved_rule_sentiment(text)
            except Exception:
                sentiment = improved_rule_sentiment(text)
        else:
            sentiment = improved_rule_sentiment(text)

        if not ticker_matches:
            continue

        if not amount_matches:
            for t in ticker_matches:
                results.append({"asset": t['ticker'], "text": text, "amount": 1, "unit": "hisse",
                                "action": action, "sentiment": sentiment})
        else:
            if len(amount_matches) == 1 and len(ticker_matches) > 1:
                amt = amount_matches[0]
                for t in ticker_matches:
                    results.append({"asset": t['ticker'], "text": text,
                                    "amount": amt['num'], "unit": amt['unit'],
                                    "action": action, "sentiment": sentiment})
            else:
                for t in ticker_matches:
                    best = None
                    best_dist = None
                    t_pos = (t['start'] + t['end']) // 2
                    for a in amount_matches:
                        a_pos = (a['start'] + a['end']) // 2
                        dist = abs(t_pos - a_pos)
                        if best is None or dist < best_dist:
                            best = a
                            best_dist = dist
                    if best is not None and best_dist <= proximity_chars:
                        results.append({"asset": t['ticker'], "text": text,
                                        "amount": best['num'], "unit": best['unit'],
                                        "action": action, "sentiment": sentiment})
                    else:
                        results.append({"asset": t['ticker'], "text": text,
                                        "amount": 1, "unit": "hisse",
                                        "action": action, "sentiment": sentiment})
    return pd.DataFrame(results)
