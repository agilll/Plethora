This is the tool to build the corpus:

- launch python3 pp_app_corpus.py

- open in browser localhost:5000/corpus

Input: a text  (initialText.txt)

It creates a KORPUS folder with results:
- Identifies DB entities in text
- Shows their Wikicats and ask the user for selection
- Finds the URLs that have such wikicats
- Fetchs such URLs and clean them (remove mark up)
- Assesses if each text is related to the initial one. If related, adds it to the corpus

It uses D2V for assessing relatedness, with a model training with an initial corpus
