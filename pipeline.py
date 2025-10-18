# pipeline.py
import re
import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher

# ---------- ticker ve fallback
def get_bist_tickers():
    try:
        from pykap.bist_company_list import bist_company_list
        return bist_company_list()
    except:
        return ["AVISA", "THYAO", "GARAN", "SASA", "AHGAZ"]

# ---------- sayı parse
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

# ---------- miktar / birim
def extract_amounts(text, units):
    pattern = r'(?P<num>\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?|\d+)\s*(?P<unit>' + '|'.join(map(re.escape, units)) + r')\b'
    matches = []
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        num = parse_number(m.group('num'))
        unit = m.group('unit').lower()
        matches.append({"num": num, "unit": unit, "start": m.start(), "end": m.end(), "text": m.group(0)})
    perc_pattern = r'([+-]?\d+[.,]?\d*)\s*%'
    for m in re.finditer(perc_pattern, text, flags=re.IGNORECASE):
        num = parse_number(m.group(1))
        matches.append({"num": num, "unit": "%", "start": m.start(), "end": m.end(), "text": m.group(0)})
    return sorted(matches, key=lambda x: x['start'])

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

# ---------- gelişmiş sentiment
POS_WORDS = [
    "iyi","kazanç","kazandım","kâr","kârlı","pozitif","mutlu","harika","yükseldi","arttı","kârda",
    "gelir","reel artış","kazançlı","artıyor","toparlanıyor"
]
NEG_WORDS = [
    "düşüş","düştü","zarar","negatif","kötü","azaldı","kaybettim","problem","sıkıntı","eksilerde",
    "düşüyor","durgun","kaybetti","zayıf"
]
NEGATION_WORDS = ["ama","fakat","ancak","ne var ki","lakin"]

def comprehensive_sentiment(text):
    t = text.lower()
    pos_score = sum(t.count(w) for w in POS_WORDS)
    neg_score = sum(t.count(w) for w in NEG_WORDS)
    for m in re.finditer(r'([+-]?\d+[.,]?\d*)\s*(%|tl|₺)', t):
        val = float(m.group(1).replace(',', '.'))
        if val > 0:
            pos_score += 1
        elif val < 0:
            neg_score += 1
    for neg_word in NEGATION_WORDS:
        parts = t.split(neg_word)
        if len(parts) > 1:
            after_neg = parts[1]
            after_pos = sum(after_neg.count(w) for w in POS_WORDS)
            after_neg_score = sum(after_neg.count(w) for w in NEG_WORDS)
            pos_score += after_neg_score
            neg_score += after_pos
    if pos_score > neg_score:
        return "positive"
    elif neg_score > pos_score:
        return "negative"
    else:
        return "neutral"

# ---------- ticker tespiti
def find_tickers(text, tickers, company_to_ticker=None):
    found = []
    tickers_sorted = sorted(set(tickers), key=lambda x: -len(x))
    for t in tickers_sorted:
        pattern = r'(?<!\w)' + re.escape(t) + r'(?!\w)'
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.append({"ticker": t, "start": m.start(), "end": m.end(), "match": m.group(0)})
    if company_to_ticker:
        nlp = spacy.blank("tr")
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        patterns = [nlp.make_doc(name) for name in company_to_ticker.keys()]
        matcher.add("COMP", patterns)
        doc = nlp(text)
        for match_id, start, end in matcher(doc):
            span = doc[start:end]
            ticker = company_to_ticker.get(span.text)
            if ticker:
                found.append({"ticker": ticker, "start": span.start_char, "end": span.end_char, "match": span.text})
    return found

# ---------- ana analiz fonksiyonu
def analyze_texts(texts, tickers=None, units=None, company_to_ticker=None):
    if units is None:
        units = ["hisse","hissesi","adet","tane","lot","pay","birim","payı","paylar","lotu","lotlar","lotları"]
    if tickers is None:
        tickers = get_bist_tickers()
    results = []
    for text in texts:
        amount_matches = extract_amounts(text, units)
        ticker_matches = find_tickers(text, tickers, company_to_ticker=company_to_ticker)
        action = detect_action(text)
        sentiment = comprehensive_sentiment(text)
        if not ticker_matches:
            continue
        if not amount_matches:
            for t in ticker_matches:
                results.append({"asset": t['ticker'], "text": text, "amount": 1, "unit": "hisse", "action": action, "sentiment": sentiment})
        else:
            if len(amount_matches) == 1 and len(ticker_matches) > 1:
                amt = amount_matches[0]
                for t in ticker_matches:
                    results.append({"asset": t['ticker'], "text": text, "amount": amt['num'], "unit": amt['unit'], "action": action, "sentiment": sentiment})
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
                    if best is not None and best_dist <= 60:
                        results.append({"asset": t['ticker'], "text": text, "amount": best['num'], "unit": best['unit'], "action": action, "sentiment": sentiment})
                    else:
                        results.append({"asset": t['ticker'], "text": text, "amount": 1, "unit": "hisse", "action": action, "sentiment": sentiment})
    return pd.DataFrame(results)
