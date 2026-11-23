"""NLP matching: text preprocessing, TF-IDF, cosine similarity and the weighted score.

    S = 0.70*T + 0.20*L + 0.10*D
    T = TF-IDF cosine similarity of descriptions
    L = location similarity,  D = date proximity
"""
import re
from datetime import date

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

STOP_WORDS = set(ENGLISH_STOP_WORDS) | {"lost", "found", "item", "please", "near", "left", "got", "like"}


def _stem(word: str) -> str:
    """Very light suffix stripping so 'earbuds' ~ 'earbud'."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def preprocess(text: str) -> str:
    """Lowercase, strip punctuation, drop stop words, light stemming."""
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return " ".join(_stem(t) for t in tokens if t not in STOP_WORDS and len(t) > 1)


def keyword_overlap(reference: str, candidate: str):
    """Fraction of the reference's keywords that appear in the candidate (None if no keywords)."""
    ref = set(preprocess(reference).split())
    if not ref:
        return None
    return len(ref & set(preprocess(candidate).split())) / len(ref)


def text_similarity_pair(a: str, b: str) -> float:
    """TF-IDF cosine similarity between two texts."""
    docs = [preprocess(a), preprocess(b)]
    try:
        x = TfidfVectorizer().fit_transform(docs)
    except ValueError:
        return 0.0
    return float(cosine_similarity(x[0], x[1])[0, 0])


def location_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    za, zb = config.LOCATION_ZONES.get(a), config.LOCATION_ZONES.get(b)
    return config.SAME_ZONE_SCORE if za and za == zb else 0.0


def date_proximity(a, b) -> float:
    da = a if isinstance(a, date) else date.fromisoformat(str(a))
    db_ = b if isinstance(b, date) else date.fromisoformat(str(b))
    return max(0.0, 1.0 - abs((da - db_).days) / config.DATE_WINDOW_DAYS)


def weighted_score(t: float, l: float, d: float) -> float:
    return config.W_TEXT * t + config.W_LOC * l + config.W_DATE * d


def score_matrix(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """Score every row of `a` against every row of `b`.

    Both frames need item_name, description, location and date columns.
    Returns matrices T, L, D, S of shape (len(a), len(b)).
    """
    shape = (len(a), len(b))
    if 0 in shape:
        z = np.zeros(shape)
        return {"T": z, "L": z, "D": z, "S": z}
    docs = [preprocess(f"{r.item_name} {r.description}") for r in a.itertuples()]
    docs += [preprocess(f"{r.item_name} {r.description}") for r in b.itertuples()]
    try:
        x = TfidfVectorizer().fit_transform(docs)               # TF-IDF vectors
        t = cosine_similarity(x[: len(a)], x[len(a):])          # cosine similarity
    except ValueError:                                          # no usable words at all
        t = np.zeros(shape)
    l = np.array([[location_similarity(la, lb) for lb in b["location"]] for la in a["location"]])
    d = np.array([[date_proximity(da, db_) for db_ in b["date"]] for da in a["date"]])
    return {"T": t, "L": l, "D": d, "S": config.W_TEXT * t + config.W_LOC * l + config.W_DATE * d}


def rank_matches(query: dict, candidates: pd.DataFrame, top_n: int = config.TOP_N) -> pd.DataFrame:
    """Return the top-N candidate reports for one query item, best first."""
    cols = ["report_id", "item_name", "category", "location", "date",
            "text_sim", "loc_sim", "date_sim", "score"]
    if candidates.empty:
        return pd.DataFrame(columns=cols)
    m = score_matrix(pd.DataFrame([query]), candidates.reset_index(drop=True))
    out = candidates.reset_index(drop=True).copy()
    out["text_sim"], out["loc_sim"] = m["T"][0], m["L"][0]
    out["date_sim"], out["score"] = m["D"][0], m["S"][0]
    return out.sort_values("score", ascending=False).head(top_n)[cols].reset_index(drop=True)
