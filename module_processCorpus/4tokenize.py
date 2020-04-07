#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script tokenizes .w files to get .t files
# a .w file is a text file that has been preprocessed with previous scripts
# a .t file is a binary file, saved with pickle, containing a list of lists of words

# tokenize is to convert the text in a list of sentences, each sentence being a list of words

# input: a .w file or a folder (the CORPUS base)
#         if folder, folder/files_s_p_w must exist, and all '.w' files in folder/files_s_p_w will be processed 
# output: a .t file per .w file, where text has been changed by a list of lists of words (saved in binary with pickle)
#         in case a folder, folder/files_t will be created to store results

# Requires the Stanford Core NLP server to be started and listening in port 9000
# get into the Stanford Core NLP folder and execute
# java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000 -timeout 15000 &

import nltk
import re
import pickle
import os
import sys

sys.path.append('../')  # to search for imported files in the parent folder

from px_aux import StanfordBroker as _StanfordBroker

from aux import  SPW_FOLDER as _SPW_FOLDER, T_FOLDER as _T_FOLDER


# to process a file to convert sentences to lists of words
# returns a global list, composed of lists of words, each per sentence
def processOneFile (filename):
	fp = open(filename)
	data = fp.read()
	
	tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')  	# tokenizer is a Tokenizer pretrained for English
	sentences = tokenizer.tokenize(data.strip(), realign_boundaries=True)  # list of sentences in data (strip removes leading and trailing spaces)
	
	sentencesTokenizedLower = []   # final result, list of lists of words
	
	stanfordBroker = _StanfordBroker()
		
	# to remove from list of words 
	punctuation = ['.', ',', '?', '¿', ')', '(', ']', '[', '\'', '/', '%', '...', '$', '–', '=', '‘', '¡', '!', '`', '´', ':', ';', '’', '--', '``', '´´', "''", '-', '\'s', "'"]
	abrev = ["bc", "ac", "b.c.e.", "etc.", "i.e.", "e.g.", "cf.", "mt.", "st.", "mr.", "ms.", "dr.", "u.s."] # heuristic set of words to discard
	toRemove = punctuation + abrev
	avoidedPOS = ["PRP", "PRP$", "TO", "IN", "DT", "CC", "SYM", "UH", "CD"] # complete? should be reviewed

	for sentence in sentences:   # each sentence is a string from the file
			
		words = stanfordBroker.identifyWords(sentence)  # returns a list with a dict for each word with keys originalText, lemma and pos (POS), among others
	
		lemmasSentenceLower = []   # list of lemmas of words in a sentence, in lower-case
		for word in words: # word is each of the distinct words identified in each sentence
			lemma = word["lemma"].lower()  # lemma is the canonical form of word in lower-case (lower required because of proper names)
			
			if (len(lemma) == 0) or (word["originalText"] in toRemove) or (lemma in toRemove) or (word["pos"] in avoidedPOS):
				continue
			
			isNumber = re.search("^[\+\-]?\d*[\.\,]?\d+(?:[Ee][\+\-]?\d+)?$", lemma)  # return the match if a number, or None otherwise
			if isNumber:
				continue
				
			initials = re.search("^\w\.\w\.", lemma)  # to discard initials, for instance d.a.
			if initials:
				continue
			
			isGarbage = re.search("^\W+.*$", lemma)   # to discard garbage, set of characters not beginning with letter
			if isGarbage:
				continue

			lemmasSentenceLower.append(lemma)   # add word to the current list of words
	
		sentencesTokenizedLower.append(lemmasSentenceLower)   # add list of words to the global list

	return sentencesTokenizedLower   # return the global list





# start processing

# parameter checking

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
		source = sys.argv[1]  # this is the file|folder with the source data
# error if more than one param
else:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

	


# process a file
if os.path.isfile(source):
	print("Processing file "+source+"...\n")
	result = processOneFile(source)
	pickle.dump(result, open(source+".t", "wb" ))
	
# source is a folder. It must be the base CORPUS folder
# it must exist a files_s_p_w folder inside
# process all '.w' files in source/files_s_p_w
elif os.path.isdir(source):
	spw_folder = source + _SPW_FOLDER
	if not os.path.exists(spw_folder):
		print(spw_folder, "not found!")
		exit()
	t_folder = source + _T_FOLDER
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
	print(source, "not found!")
	
