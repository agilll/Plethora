

# folders and filenames involved in corpus construction

MODELS_FOLDER = "../MODELS"
LEE_D2V_MODEL = MODELS_FOLDER+"/model_d2v_lee.model"
OWN_D2V_MODEL = MODELS_FOLDER+"/model_d2v_own-t.model"

CORPUS_FOLDER = "KORPUS"

WIKICAT_LIST_FILENAME = "WIKICAT_LIST.txt"
SELECTED_WIKICAT_LIST_FILENAME = "SELECTED_WIKICAT_LIST.txt"
URLs_FOLDER = CORPUS_FOLDER+"/URLs"
SCRAPPED_PAGES_FOLDER = CORPUS_FOLDER+"/SCRAPPED_PAGES"
SCRAPPED_TEXT_PAGES_FOLDER = CORPUS_FOLDER+"/SCRAPPED_TEXT_PAGES"
DISCARDED_PAGES_FILENAME = CORPUS_FOLDER+"/discarded_list.txt"
UNRETRIEVED_PAGES_FILENAME = CORPUS_FOLDER+"/unretrieved_pages.txt"
SIMILARITIES_CSV_FILENAME = CORPUS_FOLDER+"/similarity.csv"


HTML_PAGES_FOLDER = CORPUS_FOLDER+"/HTML_PAGES"

# # to save some ASCII content in a file 
def saveFile (f, content):
	out = open(f, 'w')
	out.write(content)
	out.close()
	return
