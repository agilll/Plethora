
from nltk.tokenize import RegexpTokenizer
import nltk
import re
import os

# folders and filenames involved in corpus construction

MODELS_FOLDER = "../MODELS"
LEE_D2V_MODEL = MODELS_FOLDER+"/model_d2v_lee.model"
OWN_D2V_MODEL = MODELS_FOLDER+"/model_d2v_own-t.model"

# initial text for corpus building
INITIAL_TEXT = 'initialText.txt'

CORPUS_FOLDER = os.getenv('HOME') + "/Google Drive/KORPUS"

# these are the files and folders created in the building of corpus

URLs_FOLDER = CORPUS_FOLDER+"/URLs"
SCRAPPED_TEXT_PAGES_FOLDER = CORPUS_FOLDER+"/SCRAPPED_TEXT_PAGES"
DISCARDED_PAGES_FILENAME = CORPUS_FOLDER+"/discarded_pages.txt"
UNRETRIEVED_PAGES_FILENAME = CORPUS_FOLDER+"/unretrieved_pages.txt"
SIMILARITIES_CSV_FILENAME = CORPUS_FOLDER+"/similarities.csv"
HTML_PAGES_FOLDER = CORPUS_FOLDER+"/HTML_PAGES"


# set of english stopwords
nltk_stopwords = nltk.corpus.stopwords.words('english')

# function to check if a word is in the English stopwords set (to be used in a filter)
def isNotStopWord (word):
	if word not in nltk_stopwords:
		return True
	return False


# to check if a dictionary has the field 'pt' (isPrimaryTopicOf), that is a dictionary that must contain the field 'value'
def hasFieldPT(x):
	try:
		x["pt"]["value"]
		return True
	except:
		return False
	


# no longer used
# function to get the N greatest elements in a list
def NmaxElements(list1, N):
	final_list = []
	
	for i in range(0, N):
		max1 = 0
		
		for j in range(len(list1)):
			if list1[j] > max1:
				max1 = list1[j];
				
		list1.remove(max1);
		final_list.append(max1)
	
	return final_list

def NmaxElements3T(list1, N):
	final_list = []
	try:
		for i in range(0, N):
			max1 = ("","",0)
			
			for j in range(len(list1)):
				if list1[j][2] > max1[2]:
					max1 = list1[j];
					
			if max1 != ("","",0):
				list1.remove(max1);
			else:
				return final_list
			final_list.append(max1)
	except Exception as e:
		print("Exception while computing NmaxElements3T:", e)
		print(list1)
	
	return final_list
###################### 			


# to reject simple wikicats, with only one component
def filterSimpleWikicats (wikicat):
	if (len(getWikicatComponents(wikicat)) == 1):
		return False
	else:
		return True
	




# Tokenize text, and returns a list of words (lowercase) after removing the stopwords
def myTokenizer (text):

	# Create a tokenizer
	tokenizer = RegexpTokenizer('\w+')

	# Tokenize text
	tokens = tokenizer.tokenize(text)

	# Get English stopwords from the NLTK (Natural Language Toolkit)
	nltk_stopwords = nltk.corpus.stopwords.words('english')

	# Change words to lower case
	text_words = list(map(lambda x: x.lower(), tokens))
	
	def isNotStopWord (word):
		if word not in nltk_stopwords:
			return True
		return False
	
	# remove the stopwords
	words_filtered = list(filter(isNotStopWord, text_words))

	return words_filtered


# to get all the single components of a wikicat
def separateWikicatComponents (wikicat):
	lista =[]
	word=""
	
	long = len(wikicat)
	idx = 0
	
	while idx < long:
		l = wikicat[idx]
		idx += 1
		
		if len(word) == 0:			# if idx=1, len(word)=0 and this continue executes
			word = word + str(l)
			continue
		
		if str(l).isdigit():
			if not str(wikicat[idx-2]).isdigit():  # idx cannot be 1
				lista.append(word)
				word = str(l)
			else:
				word = word + str(l)
			continue
				
		if l.isupper():
			if wikicat[idx-2] == '-':
				word = word + str(l)
				continue
			
			if (idx == long):
				word = word + str(l)
				continue
			
			if word.isupper():
				if wikicat[idx].islower():
					lista.append(word)
					word = str(l)
				else:
					word = word + str(l)
			else:
				if (l == 'B') and (wikicat[idx] == 'C'):
					word = word + "BC"
					idx += 1
				else:
					if (l == 'A') and (wikicat[idx] == 'D'):
						word = word + "AD"
						idx += 1;
					else:
						lista.append(word)
						word = str(l)

		else:
			word = word + str(l)
	
		
	if len(word) > 0:
		lista.append(word)
	
	return lista


# to get the relevant components of a wikicat 
def getWikicatComponents (wikicat):
	components = separateWikicatComponents(wikicat)   # get all the components
	components_lower = list(map(lambda x: x.lower(), components))  # to lowercase
	
	components_filtered = list(filter(isNotStopWord, components_lower))  # remove stopwords
	return components_filtered