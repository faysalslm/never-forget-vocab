### Never Forget Vocab
A tiny Streamlit app I’m building to make vocab stick. You get a clean flashcard for each word (meaning with connotation, synonyms/antonyms, and an example), and you can generate one sentence at a time (Easy / Moderate / Hard) to see the word in different contexts.
I built it because my wife kept forgetting GRE/IELTS words unless she saw them used in sentences. This solves that.

### What you can do
- Search a word or flip through them with Next/Back
- See a flashcard with meaning (starts with (+)/(-)/(N)), synonyms, antonyms, and one example
- Click Generate Sentence! → pick a level (Easy / Moderate / Hard)
- Generate one sentence at a time (use Generate Again for another)
- Browse the study list (10 words per page) and click a word to load it into the flashcard
- Works without any keys (demo sentences). If you add an API key, it uses a real model.

### Tech (kept simple)
- Python + Streamlit
- Pandas for the CSV
- python-dotenv for secrets
- OpenAI API (optional) for sentence generation — using gpt-4o-mini because it’s cheap and decent

## Getting it running (local)

```bash
# clone your repo and go inside
cd never-forget-vocab

# create a virtual env
python -m venv .venv
.\.venv\Scripts\activate     # Windows
source .venv/bin/activate    # macOS / Linux

# install and run
pip install -r requirements.txt
streamlit run app.py
```
Open: http://localhost:8501

### Optional: real sentences (with API)
- Create a .env file in the project root:
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini

No .env? No problem, as the app returns demo sentences so that you can click around safely.

### Data
I’m using a CSV of 1,688 GRE words my wife is studying with these columns:
- Words
- Definition
- Connotation ((+), (-), (N))
- Synonym
- Antonym
- Sentence (one example)
- Put your file here:
data/your csv.csv
If your columns differ, adjust the names in app.py where the CSV is loaded.

### Folder layout

```text
Never-Forget-Vocab/
├─ app.py
├─ requirements.txt
├─ .gitignore
├─ data/
│  └─ Word List for Webapp.csv
└─ screenshots/            # optional: for portfolio/README
   ├─ flashcard_view.png
   ├─ study_list.png
   └─ generated_sentence.png
```
.gitignore ignores .env and .venv so you don’t leak secrets or upload your whole environment. 

### Notes from building this
- Streamlit is doing both the “frontend” and the “backend” here. That’s on purpose: a fast, Python-only thing I can ship.
- The sentence generator is level-aware (Easy / Moderate / Hard). It nudges the model with rough word-count ranges.
- One sentence at a time felt better for memory than dumping paragraphs.
- I’m keeping state simple with st.session_state (no database yet). That’s intentional for the MVP.

### Troubleshooting
- App is blank or keeps restarting > Usually a syntax error. Check the terminal logs where you ran streamlit run app.py.
- Long text overflows > I added wrapping. On very small screens, widen the window or reduce zoom.
- API key errors > Remove .env to fall back to demo mode, or double-check OPENAI_API_KEY=.

### Roadmap (next)
- Spaced repetition (Leitner / SM-2) with a tiny SQLite DB
- Audio (TTS) to hear each sentence
- Export generated sentences to CSV
- A small mobile design pass

### Why this exists (short version)
Existing apps didn’t fit how my wife studies. This keeps her in one place: read the card, generate a couple of sentences, move on. Enough structure to stay focused without turning into a whole study platform.

### License
Personal project. Feel free to read the code and get ideas. If you fork it, please bring your own word list and API key.


