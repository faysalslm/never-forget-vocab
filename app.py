import os
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

try:
    from openai import OpenAI
except:
    OpenAI = None   

# page setup 
st.set_page_config(page_title="Never Forget Vocab", layout="wide")

# loading env file
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:   # for empty string 
    API_KEY = ""

# the model name. keeping it default to gpt-mini
MODEL_NAME = os.getenv("MODEL_NAME")
if not MODEL_NAME:
    MODEL_NAME = "gpt-4o-mini"

# making the client
if API_KEY and OpenAI is not None:
    CLIENT = OpenAI(api_key=API_KEY)
else:
    CLIENT = None

# putting csv file
CSV_PATH = "Word List for Webapp.csv"

# number of words per page
WORDS_PER_PAGE = 10

# cache the csv
@st.cache_data
def load_words(path: str):
    df = pd.read_csv(path)  
    df.columns = [c.strip() for c in df.columns]

    required = {"Words", "Definition", "Connotation", "Synonym", "Antonym", "Sentence"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    df["word_lc"] = df["Words"].astype(str).str.strip().str.lower()
    return df  # send back the dataframe

# loading data here
try:
    words_df = load_words(CSV_PATH)
except Exception as e:
    # show the error on the page and stop everything
    st.error(f"Could not load CSV: {e}")
    st.stop()

TOTAL = len(words_df)
TOTAL_PAGES = (TOTAL + WORDS_PER_PAGE - 1) // WORDS_PER_PAGE  # ceil without math lib


# checking if the word shows up only once in a string
def appears_once(word: str, s: str) -> bool:
    import re   # just import again here (lazy, but works)
    pattern = r"\b" + re.escape(word) + r"\b"
    found = re.findall(pattern, s, flags=re.IGNORECASE)
    return len(found) == 1   # true if exactly once


# sentence length checker
def validate_len(level: str, s: str) -> bool:
    words = s.split()
    wc = len(words)
    if level == "Easy":
        return wc >= 8 and wc <= 14
    if level == "Moderate":
        return wc >= 12 and wc <= 18
    return wc >= 15 and wc <= 25


# function that talks to openai (or makes fake demo sentence)
@st.cache_data(show_spinner=False)   # streamlit caches result
def generate_one_sentence(word: str, definition: str, level: str):
    if CLIENT is None:   # if no api client, it should show demo text
        return "(demo) Use " + word + " naturally in a " + level.lower() + " sentence."

    # difficulty bands for sentence generation
    band = {
        "Easy": "CEFR A2–B1, 8–14 words, everyday topics, common vocabulary",
        "Moderate": "IELTS 6.0–7.0, 12–18 words, natural collocations and clauses",
        "Hard": "GRE/academic tone, 15–25 words, analytical or abstract context",
    }[level]

    # building prompt for the AI
    prompt = "Generate 1 " + level + " sentence using the word '" + word + "'. " \
             + "Definition: " + definition + ". Constraints: " + band + ". " \
             + "Use the target word exactly once. Output just the sentence."

    try:
        # talk to the openai api
        resp = CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        text = resp.choices[0].message.content.strip()
        if appears_once(word, text) and validate_len(level, text):
            return text
        else:
            return text   
    except Exception as e:
        return "[Provider error] " + str(e)


# function to get slice of the big dataframe for paging
def get_page_slice(page_idx: int):
    # start index.. just multiply
    start = page_idx * WORDS_PER_PAGE
    # end index, dont go over total
    end = min(start + WORDS_PER_PAGE, TOTAL)
    # return a tuple (i hope this is fine)
    return words_df.iloc[start:end], start, end


# session state (keeping default values here)
ss = st.session_state
if "page_idx" not in ss:
    ss["page_idx"] = 0
if "current_word" not in ss:
    ss["current_word"] = words_df.iloc[0]["Words"]
if "show_levels" not in ss:
    ss["show_levels"] = False
if "generated" not in ss:
    ss["generated"] = []    # list for storing generated sentences
if "last_level" not in ss:
    ss["last_level"] = "Easy"
if "last_search" not in ss:
    ss["last_search"] = ""


# adding css
st.markdown("""
<style>
/* buttons primary vs secondary colors */
.stButton > button[kind="primary"]{
  background: #2563eb !important;
  color: white !important;
  border: 0 !important;
}
.stButton > button[kind="secondary"]{
  background: #f3f4f6 !important;
  color:#111827 !important;
  border:1px solid #e5e7eb !important;
}

[data-testid="stDataFrame"] div[role="gridcell"]{
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
}
</style>
""", unsafe_allow_html=True)


# header and subtitle text
st.markdown(
    "<h2 style='text-align:center;margin-bottom:0;'>Never Forget Vocab</h2>"
    "<p style='text-align:center;color:#666;margin-top:4px;'>"
    "Giving up is not an option. Memorizing vocab is fun if you understand it well enough!"
    "</p>",
    unsafe_allow_html=True
)


# search bar
q_col = st.columns([1,2,1])[1]   
with q_col:
    q = st.text_input("Type a word to jump to it",
                      placeholder="Type a word to jump to it",
                      label_visibility="collapsed")

if q and q != ss["last_search"]:
    matches = words_df[words_df["word_lc"].str.contains(q.strip().lower())]
    if not matches.empty:
        first_idx = matches.index[0]
        # update session stuff
        ss["current_word"] = matches.iloc[0]["Words"]
        ss["page_idx"] = first_idx // WORDS_PER_PAGE
        ss["generated"] = []
        ss["show_levels"] = False
    ss["last_search"] = q


# flashcard part (one word card with details from CSV)
page_df, start, end = get_page_slice(ss["page_idx"])
row = words_df.loc[words_df["Words"] == ss["current_word"]].iloc[0]

connotation = str(row["Connotation"]).strip()
definition = str(row["Definition"]).strip()
synonyms = str(row["Synonym"]).strip()
antonyms = str(row["Antonym"]).strip()
example = str(row["Sentence"]).strip()


nav_l, card_col, nav_r = st.columns([1,6,1])

with nav_l:
    current_idx = words_df.index[words_df["Words"] == ss["current_word"]][0]
    st.button("⬅ Back",
              use_container_width=True,
              disabled=(current_idx == 0),
              key="back_btn",
              type="secondary",
              on_click=lambda: ss.update(
                  current_word=words_df.iloc[max(0, current_idx-1)]["Words"],
                  page_idx=(max(0, current_idx-1)) // WORDS_PER_PAGE,
                  generated=[],
                  show_levels=False
              ))

with nav_r:
    last_index = TOTAL - 1
    st.button("Next ➡",
              use_container_width=True,
              disabled=(current_idx == last_index),
              key="next_btn",
              type="secondary",
              on_click=lambda: ss.update(
                  current_word=words_df.iloc[min(last_index, current_idx+1)]["Words"],
                  page_idx=(min(last_index, current_idx+1)) // WORDS_PER_PAGE,
                  generated=[],
                  show_levels=False
              ))

with card_col:
    # card HTML
    st.markdown(
        """
        <div style="border:1px solid #eee;padding:18px 22px;border-radius:14px;">
            <h3 style="margin:0 0 8px 0;">{word}</h3>
            <p style="margin:6px 0 12px 0;font-size:1.05rem;"><b>{con}</b> {defn}</p>
            <p style="margin:4px 0;"><b>Synonyms:</b> <span style="color:#2c7a7b;">{syn}</span></p>
            <p style="margin:2px 0 10px 0;"><b>Antonyms:</b> <span style="color:#c53030;">{ant}</span></p>
            <p style="margin:2px 0;"><b>Sentence:</b> {ex}</p>
        </div>
        """.format(
            word=ss["current_word"],
            con=connotation,
            defn=definition,
            syn=synonyms,
            ant=antonyms,
            ex=example
        ),
        unsafe_allow_html=True
    )


# generate sentence section
center = st.columns([1,2,1])[1]
with center:
    if st.button("Generate Sentence!", use_container_width=True, type="primary"):
        ss["show_levels"] = True

    if ss["show_levels"]:
        # 3 buttons side by side
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🟢 Easy", use_container_width=True, type="secondary"):
                ss["last_level"] = "Easy"
                s = generate_one_sentence(ss["current_word"], definition, "Easy")
                ss["generated"].append((s, "Easy"))

        with col2:
            if st.button("🔵 Moderate", use_container_width=True, type="secondary"):
                ss["last_level"] = "Moderate"
                s = generate_one_sentence(ss["current_word"], definition, "Moderate")
                ss["generated"].append((s, "Moderate"))

        with col3:
            if st.button("🔴 Hard", use_container_width=True, type="secondary"):
                ss["last_level"] = "Hard"
                s = generate_one_sentence(ss["current_word"], definition, "Hard")
                ss["generated"].append((s, "Hard"))

        if ss["generated"]:
            st.caption("Current level: **" + ss["last_level"] + "**")
            st.markdown("### Generated Sentences")

            for i,(txt,lvl) in enumerate(ss["generated"], start=1):
                st.text_area("Sentence " + str(i) + " (" + lvl + ")", value=txt, height=70)

            if st.button("Generate Again"):
                lvl = ss["last_level"]
                s = generate_one_sentence(ss["current_word"], definition, lvl)
                ss["generated"].append((s, lvl))



# study table
st.markdown("---")
st.subheader("Study List (10 per page)")

col_a, col_b, col_c = st.columns([1,1,6])
with col_a:
    if st.button("⬅ Prev Page", disabled=ss["page_idx"]==0, use_container_width=True, type="secondary"):
        ss["page_idx"] -= 1

with col_b:
    if st.button("Next Page ➡", disabled=ss["page_idx"] >= TOTAL_PAGES-1, use_container_width=True, type="secondary"):
        ss["page_idx"] += 1

with col_c:
    pg = st.number_input("Go to page", min_value=1, max_value=TOTAL_PAGES, value=ss["page_idx"]+1, step=1)
    if pg-1 != ss["page_idx"]:
        ss["page_idx"] = int(pg-1)


page_df, start, end = get_page_slice(ss["page_idx"])

# meaning = connotation + definition
display_df = page_df.copy()
display_df["Meaning"] = display_df["Connotation"].astype(str).str.strip() + " " + display_df["Definition"].astype(str).str.strip()
display_df = display_df[["Words", "Meaning", "Synonym", "Antonym", "Sentence"]]

display_df.insert(0, "No.", range(start+1, end+1))

row_h = 44
df_height = 62 + row_h * len(display_df)   # header + rows

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,   
    height=df_height,
    column_config={
        "No.": st.column_config.NumberColumn("No.", width="small"),
        "Words": st.column_config.TextColumn("Words", width="small"),
        "Meaning": st.column_config.TextColumn("Meaning", width="medium"),
        "Synonym": st.column_config.TextColumn("Synonym", width="medium"),
        "Antonym": st.column_config.TextColumn("Antonym", width="medium"),
        "Sentence": st.column_config.TextColumn("Sentence", width="large"),
    }
)

# clickable buttons for each word
st.caption("Click a word below to load it into the flashcard:")
btn_cols = st.columns(5)
for i, (_, r) in enumerate(page_df.iterrows()):
    with btn_cols[i % 5]:
        if st.button(r["Words"], key="pick_" + r["Words"], type="secondary"):
            ss["current_word"] = r["Words"]
            ss["generated"] = []
            ss["show_levels"] = False

