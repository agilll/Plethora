#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script trains a Word2Vec model from all'.t' files contained in the TRAINING_T_FOLDER folder (../CORPUS/files_t/ by default)
# saves the model in the current folder

import gensim
from gensim.models import Word2Vec
import pickle
import os
from os.path import isfile
import sys

from aux import TRAINING_T_FOLDER as _TRAINING_T_FOLDER
	
#check that folder with T files exists
if not os.path.exists(_TRAINING_T_FOLDER):
	print("Folder with .t files not found! (", _TRAINING_T_FOLDER, ")")
	exit()
	
# class that provides an object to read sentences from .t files (one or all in a folder), and yield them for training
class MySentences ():
	def __init__(self, source):   # source can be a file or a folder
		self.source = source

	def __iter__(self):
		cont_yields=0
		if isfile(self.source): 	# parameter is a file, yield its contents 
			if not self.source.endswith(".t"):
				print("The file "+self.source+" has not '.t' extension")
				exit(-1)
			sentencesList = pickle.load(open(self.source, "rb" ))
			for sentence in sentencesList:
				cont_yields += 1
				yield sentence
		else:						# parameter is a folder, yield the contents of all its .t files	
			cont_files=0
			for fname in sorted(os.listdir(self.source)):
				if not fname.endswith(".t"):
					continue
				else:
					cont_files += 1
					sentencesList = pickle.load(open(self.source+"/"+fname, "rb" ))
					for sentence in sentencesList:
						cont_yields += 1
						yield sentence
			print(cont_files, "files!")
		print(cont_yields, "yields!")


# function to train
def trainAndSave(sentences, w, m_c, i):
	name = "agil_W" + str(w) + "_MC" + str(m_c) + "_I"+str(i)
	print("Training "+name)
	m = Word2Vec(sentences, size=300, workers=4, window=w, min_count=m_c, iter=i)   # always 300 neurons
	m.save(name)


# start training

# get the sample generator
sentencesStream = MySentences(_TRAINING_T_FOLDER)

# train
trainAndSave(sentencesStream, 10, 10, 1000)   # window=10, min_word_count=10, 1000 epochs
	


