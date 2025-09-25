import os
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Optional OpenAI (runs in demo mode if no key)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# --------------------
# Config & setup
# --------------------
st.set_page_config(page_title="Never Forget Vocab", page_icon="📝", layout="wide")
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")  # low-cost, good quality
CLIENT = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI is not None) else None

CSV_PATH = "Word List for Webapp.csv"
WORDS_PER_PAGE = 10

# --------------------
# Data
# --------------------
@st.cache_data
def load_words(path: str):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    required = {"Words", "Definition", "Connotation", "Synonym", "Antonym", "Sentence"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    df["word_lc"] = df["Words"].astype(str).str.strip().str.lower()
    return df

try:
    words_df = load_words(CSV_PATH)
except Exception as e:
    st.error(f"Could not load CSV: {e}")
    st.stop()

TOTAL = len(words_df)
TOTAL_PAGES = (TOTAL + WORDS_PER_PAGE - 1) // WORDS_PER_PAGE

# --------------------
# Helpers
# --------------------
def appears_once(word: str, s: str) -> bool:
    pattern = rf"\b{re.escape(word)}\b"
    return len(re.findall(pattern, s, flags=re.IGNORECASE)) == 1

def validate_len(level: str, s: str) -> bool:
    wc = len(s.split())
    if level == "Easy": return 8 <= wc <= 14
    if level == "Moderate": return 12 <= wc <= 18
    return 15 <= wc <= 25  # Hard

@st.cache_data(show_spinner=False)
def generate_one_sentence(word: str, definition: str, level: str):
    """Return one sentence. Demo if no API key."""
    if CLIENT is None:
        return f"(demo) Use {word} naturally in a {level.lower()} sentence."
    band = {
        "Easy": "CEFR A2–B1, 8–14 words, everyday topics, common vocabulary",
        "Moderate": "IELTS 6.0–7.0, 12–18 words, natural collocations and clauses",
        "Hard": "GRE/academic tone, 15–25 words, analytical or abstract context",
    }[level]
    prompt = (
        f"Generate 1 {level} sentence using the word '{word}'. "
        f"Definition: {definition}. Constraints: {band}. "
        "Use the target word exactly once. Output just the sentence."
    )
    try:
        resp = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        text = resp.choices[0].message.content.strip()
        if appears_once(word, text) and validate_len(level, text):
            return text
        return text
    except Exception as e:
        return f"[Provider error] {e}"

def get_page_slice(page_idx: int):
    start = page_idx * WORDS_PER_PAGE
    end = min(start + WORDS_PER_PAGE, TOTAL)
    return words_df.iloc[start:end], start, end

# --------------------
# Session state
# --------------------
if "page_idx" not in st.session_state:
    st.session_state.page_idx = 0
if "current_word" not in st.session_state:
    st.session_state.current_word = words_df.iloc[0]["Words"]
if "show_levels" not in st.session_state:
    st.session_state.show_levels = False
if "generated" not in st.session_state:
    st.session_state.generated = []  # list of (sentence, level)
if "last_level" not in st.session_state:
    st.session_state.last_level = "Easy"
if "last_search" not in st.session_state:
    st.session_state.last_search = ""

# --------------------
# Global styles (table wrapping)
# --------------------
st.markdown(
    """
    <style>
        /* Make st.table wrap long text nicely */
        table { table-layout: fixed !important; }
        th, td { white-space: normal !important; word-break: break-word !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------
# Header / Search
# --------------------
with st.container():
    st.markdown(
        "<h2 style='text-align:center;margin-bottom:0;'>📄 Never Forget Vocab</h2>"
        "<p style='text-align:center;color:#666;margin-top:4px;'>"
        "Giving up is not an option. Memorizing vocab is fun if you understand it well enough!"
        "</p>",
        unsafe_allow_html=True
    )

search_col = st.columns([1,2,1])[1]
with search_col:
    q = st.text_input(
        "Search vocabulary...",
        placeholder="Type a word to jump to it",
        label_visibility="collapsed",
        key="search"
    )

# Handle search (no callbacks, no rerun calls)
if q and q != st.session_state.last_search:
    matches = words_df[words_df["word_lc"].str.contains(q.strip().lower())]
    if not matches.empty:
        idx = matches.index[0]
        st.session_state.current_word = matches.iloc[0]["Words"]
        st.session_state.page_idx = idx // WORDS_PER_PAGE
        # reset sentences when switching words via search
        st.session_state.generated = []
        st.session_state.show_levels = False
    st.session_state.last_search = q  # remember last query so we don't loop

# --------------------
# Flashcard
# --------------------
page_df, start, end = get_page_slice(st.session_state.page_idx)
row = words_df.loc[words_df["Words"] == st.session_state.current_word].iloc[0]

connotation = str(row["Connotation"]).strip()
definition  = str(row["Definition"]).strip()
synonyms    = str(row["Synonym"]).strip()
antonyms    = str(row["Antonym"]).strip()
example     = str(row["Sentence"]).strip()

nav_l, card_col, nav_r = st.columns([1,6,1])

with nav_l:
    current_idx = words_df.index[words_df["Words"] == st.session_state.current_word][0]
    if st.button("⬅ Back", use_container_width=True, disabled=(current_idx == 0)):
        new_idx = max(0, current_idx - 1)
        st.session_state.current_word = words_df.iloc[new_idx]["Words"]
        st.session_state.page_idx = new_idx // WORDS_PER_PAGE
        st.session_state.generated = []
        st.session_state.show_levels = False

with nav_r:
    last_index = TOTAL - 1
    if st.button("Next ➡", use_container_width=True, disabled=(current_idx == last_index)):
        new_idx = min(last_index, current_idx + 1)
        st.session_state.current_word = words_df.iloc[new_idx]["Words"]
        st.session_state.page_idx = new_idx // WORDS_PER_PAGE
        st.session_state.generated = []
        st.session_state.show_levels = False

with card_col:
    st.markdown(
        f"""
        <div style="border:1px solid #eee;padding:18px 22px;border-radius:14px;">
            <h3 style="margin:0 0 8px 0;">{st.session_state.current_word}</h3>
            <p style="margin:6px 0 12px 0;font-size:1.05rem;"><b>{connotation}</b> {definition}</p>
            <p style="margin:4px 0;"><b>Synonyms:</b> <span style="color:#2c7a7b;">{synonyms}</span></p>
            <p style="margin:2px 0 10px 0;"><b>Antonyms:</b> <span style="color:#c53030;">{antonyms}</span></p>
            <p style="margin:2px 0;"><b>Sentence:</b> {example}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# --------------------
# Generate Section
# --------------------
center = st.columns([1,2,1])[1]
with center:
    if st.button("Generate Sentence!", use_container_width=True):
        st.session_state.show_levels = True

    if st.session_state.show_levels:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🟢 Easy", use_container_width=True):
                st.session_state.last_level = "Easy"
                s = generate_one_sentence(st.session_state.current_word, definition, "Easy")
                st.session_state.generated.append((s, "Easy"))
        with c2:
            if st.button("🔵 Moderate", use_container_width=True):
                st.session_state.last_level = "Moderate"
                s = generate_one_sentence(st.session_state.current_word, definition, "Moderate")
                st.session_state.generated.append((s, "Moderate"))
        with c3:
            if st.button("🔴 Hard", use_container_width=True):
                st.session_state.last_level = "Hard"
                s = generate_one_sentence(st.session_state.current_word, definition, "Hard")
                st.session_state.generated.append((s, "Hard"))

        if st.session_state.generated:
            st.caption(f"Current level: **{st.session_state.last_level}**")
            st.markdown("### Generated Sentences")
            for i, (s_text, s_level) in enumerate(st.session_state.generated, 1):
                st.text_area(f"Sentence {i} ({s_level})", value=s_text, height=70)
            if st.button("Generate Again", help="Uses the last selected difficulty"):
                lvl = st.session_state.last_level
                s = generate_one_sentence(st.session_state.current_word, definition, lvl)
                st.session_state.generated.append((s, lvl))

# --------------------
# Study List (10 per page)
# --------------------
st.markdown("---")
st.subheader("Study List (10 per page)")

col_a, col_b, col_c = st.columns([1,1,6])
with col_a:
    if st.button("⬅ Prev Page", disabled=st.session_state.page_idx == 0, use_container_width=True):
        st.session_state.page_idx -= 1
with col_b:
    if st.button("Next Page ➡", disabled=st.session_state.page_idx >= TOTAL_PAGES - 1, use_container_width=True):
        st.session_state.page_idx += 1
with col_c:
    pg = st.number_input("Go to page", min_value=1, max_value=TOTAL_PAGES, value=st.session_state.page_idx + 1, step=1)
    if pg - 1 != st.session_state.page_idx:
        st.session_state.page_idx = int(pg - 1)

page_df, start, end = get_page_slice(st.session_state.page_idx)

# Build display with connotation merged into meaning + numbering 1..10 for the page
display_df = page_df.copy()
display_df["Meaning"] = display_df["Connotation"].astype(str).str.strip() + " " + display_df["Definition"].astype(str).str.strip()
display_df = display_df[["Words", "Meaning", "Synonym", "Antonym", "Sentence"]]
display_df.insert(0, "No.", range(start + 1, end + 1))  # 1-based numbering

# Use st.table so text wraps and there are no padded blank rows
st.table(display_df)

# Clickable word buttons (immediate flashcard load)
st.caption("Click a word below to load it into the flashcard:")
btn_cols = st.columns(5)
for i, (_, r) in enumerate(page_df.iterrows()):
    col = btn_cols[i % 5]
    with col:
        if st.button(r["Words"], key=f"pick_{r['Words']}"):
            st.session_state.current_word = r["Words"]
            st.session_state.generated = []
            st.session_state.show_levels = False
