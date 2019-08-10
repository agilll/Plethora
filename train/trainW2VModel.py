#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script trains Word2Vec models from one or several (folder) '.t' files
# saves the model in the current folder

import gensim
from gensim.models import Word2Vec
import pickle
import os
from os.path import isfile
import sys

from aux import CORPUS_FOLDER as _CORPUS_FOLDER
if not os.path.exists(_CORPUS_FOLDER):
	print(_CORPUS_FOLDER, "not found!")
	exit()
	
from aux import TRAINING_T_FOLDER as _TRAINING_T_FOLDER
if not os.path.exists(_TRAINING_T_FOLDER):
	print(_TRAINING_T_FOLDER, "not found!")
	exit()
	
	
class MySentences (object):
	def __init__(self, source):
		self.source = source

	def __iter__(self):
		cont=0
		if isfile(self.source):
			if not self.source.endswith(".t"):
				print("The file "+self.source+" has not '.t' extension")
				exit(-1)
			sentencesList = pickle.load(open(self.source, "rb" ))
			for sentence in sentencesList:
				yield sentence
		else:
			for fname in sorted(os.listdir(self.source)):
				if not fname.endswith(".t"):
					continue
				else:
					sentencesList = pickle.load(open(self.source+"/"+fname, "rb" ))
					for sentence in sentencesList:
						cont += 1
						yield sentence
		print(cont, "yields")


def trainAndSave(sentences, w, m_c, i):
	name = "agil_W" + str(w) + "_MC" + str(m_c) + "_I"+str(i)
	print("Training "+name)
	m = Word2Vec(sentences, size=300, workers=4, window=w, min_count=m_c, iter=i)   # always 300 neurons
	m.save(name)


# start training
sentencesStream = MySentences(_TRAINING_T_FOLDER)
trainAndSave(sentencesStream, 10, 10, 1000)
	


