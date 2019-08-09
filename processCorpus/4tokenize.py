#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script tokenizes .w files to get .t files
# tokenize is to convert the text in a list of sentences, where each sentence is a list of words

# input: a .w file or a folder with several .w files
# output: a .t file per .w file, where text has benn changed by a list of lists of words (saved in binary with pickle)

from nltk.stem.porter import *
from nltk.tokenize import word_tokenize, RegexpTokenizer
import nltk
import re
import pickle
import os
import sys
sys.path.append('../')

from px_aux import StanfordBroker as _StanfordBroker

SPW_FOLDER = "/files_s_p_w/"
T_FOLDER = "/files_t/"

def processOneFile (filename):
	fp = open(filename)
	data = fp.read()
	
	stanfordBroker = _StanfordBroker()
	
	# to remove from list of words
	puntuation = ['.', ',', '?', '¿', ')', '(', ']', '[', '\'', '/', '%', '...', '$', '–', '=', '‘', '¡', '!', '´', ':', ';', '’', '--', '``', "''", '-', '\'s', "'", "bc", "b.c.e.", "etc.", "i.e.", "e.g.", "cf.", "mt.", "st.", "mr.", "ms.", "dr."]
	
	tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
	sentences = tokenizer.tokenize(data.strip(), realign_boundaries=True)  # sentence list
	totalSentences = len(sentences)
	
	# a 3-group match is supposed to received, and the second is returned (to remove the third if a dot, but I don't see happening)  
	def remove_last_punt(match):
		return match.group(2)
	
	sentencesTokenizedLower = []
	
	for sentence in sentences:   # each sentence is a string  
		palabras = stanfordBroker.identifyWords(sentence)
	
		lemmasSentenceLower = []   # list of lemmas of words in a sentence, in lower-case
		for palabra in palabras: # palabra are the distinct words identified in sentence
			lemma = palabra["lemma"].lower()  # lemma is the canonical form of palabra in lower-case 
				
			isNumber = re.search("(\d)+\D?(\d)*", lemma)  # return the match if a number, or None otherwise
			
			# remove certain words from text  
			if palabra["originalText"] not in puntuation and lemma not in puntuation and len(lemma) > 0 and palabra["pos"] not in [",", ".", "PRP", "PRP$", "TO", "IN", "DT", "CC", "SYM", "UH"] and not isNumber:
				removedPunt = re.sub("(\W*)([a-zA-Z_0-9].*[a-zA-Z_0-9])(\W*)", remove_last_punt, lemma) # removes ending dot if exists
				lemmasSentenceLower.append(removedPunt)
	
		sentencesTokenizedLower.append(lemmasSentenceLower)
	
	sentecesLowerTrain = sentencesTokenizedLower
	return sentecesLowerTrain







# at least, one param
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

# if only one param, cannot start by '-'
if len(sys.argv) == 2:
	if sys.argv[1][0] == "-":
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
	else:
		parametro = sys.argv[1]
# error if more than one param
else:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

	
	
# start processing

# process a file
if os.path.isfile(parametro):
	if not parametro.endswith(".w"):
		print("The file "+parametro+" has not '.w' extension")
		exit(-1)
	print("Processing file "+parametro+"...\n")
	result = processOneFile(parametro)
	pickle.dump(result, open(parametro+".t", "wb" ))
	
# process a folder  
elif os.path.isdir(parametro):
	spw_folder = parametro + SPW_FOLDER
	if not os.path.exists(spw_folder):
		print(spw_folder, "not found!")
		exit()
	t_folder = parametro + T_FOLDER
	if not os.path.exists(t_folder):
		os.makedirs(t_folder)
	
	print("Processing folder "+spw_folder+"...")
	numFiles = 0
	for filename in sorted(os.listdir(spw_folder)):
		if not filename.endswith(".w"):
			continue
		else:
			numFiles += 1
			print("\n", numFiles, " **************** Processing file ", spw_folder+ filename+"...\n")
			result = processOneFile(spw_folder+filename)
			pickle.dump(result, open(t_folder+filename+".t", "wb" ))
		
else:
	print(parametro, "not found!")
	
