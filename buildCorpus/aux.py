

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

# initial text for corpus building
INITIAL_TEXT = 'initialText.txt'
	

# to check if a dictionary has the field 'pt' (isPrimaryTopicOf), that is a dictionary that must contain the field 'value'
def hasFieldPT(x):
	try:
		x["pt"]["value"]
		return True
	except:
		return False