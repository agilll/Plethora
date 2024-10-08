# training Doc2Vec models with .w files (preprocessed .txt files, but still text files)

import os
import sys
import collections
import glob
import csv
from smart_open import open as _Open
from datetime import datetime
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.parsing.preprocessing import remove_stopwords as Gensim_remove_stopwords
from gensim.utils import simple_preprocess
import codecs

if len(sys.argv) < 3:
	print("Use: "+sys.argv[0]+" generic_corpus percentage")
	exit(-1)

TRCORPUS = sys.argv[1]  # webbase wikipedia
pctg = sys.argv[2]
ipctg = int(pctg)

MODEL_NAME = "/Users/agil/CloudStation/KORPUS/hibrido_"+TRCORPUS+"_"+pctg+".model"
AH_CORPUS_FOLDER = "/Users/agil/CloudStation/KORPUS/SCRAPPED_PAGES/"

GEN_FOLDER_BASE = "/Users/agil/Downloads/_corpus/"
GEN_FOLDER = GEN_FOLDER_BASE+TRCORPUS+"/"

numIter=0

# read the first 8% from 1926.ph5-3.simsBest.csv: the list of ad hoc candidates
listBestAPFilename = "/Users/agil/CloudStation/KORPUS/1926/1926.ph5-3.simsBest.csv"
listAP = []

try:
    with _Open(listBestAPFilename, 'r') as csvFile:
        reader = csv.reader(csvFile, delimiter=' ')
        next(reader)  # to skip header
        for row in reader:
            listAP.append(AH_CORPUS_FOLDER+row[0])
        csvFile.close()
except Exception as e:
	print("Exception reading csvFile:", listBestAPFilename, str(e))

sizeAHCorpus = int(len(listAP) / 100) *  ipctg   # 8% of the total candidates
listCorpusAH = listAP[:sizeAHCorpus]

print("Size corpus AH =", sizeAHCorpus)



# read the generic corpus docs
listGeneric = []
if not os.path.exists(GEN_FOLDER):
	print(GEN_FOLDER, "not found!")
	quit()
else:
	listGeneric = glob.glob(GEN_FOLDER+"*.txt")	# Get all .txt files in the generic training corpus

print("Size corpus generic =", len(listGeneric))


# build the tags
dictTags = {}
for idx1,doc in enumerate(listGeneric):
	dictTags[doc] = [idx1]
for idx2,doc in enumerate(listCorpusAH, start=idx1+1): # the AH tags starts from the last of the generic
	dictTags[doc] = [idx2]



class MyCorpusBoth():
	def __init__(self):
		print("MyCorpusBoth init")
		return


	def __iter__(self):
		print("MyCorpusBoth iteration", numIter)

		startTime = datetime.now()
		print("Generic files")

		for i,file in enumerate(listGeneric):
			if (i % 100) == 0:
				print(i, end=' ', flush=True)

			with codecs.open(file, 'r', encoding='utf-8', errors='ignore') as fdata:
				text = fdata.read()
				# remove stopwords
				cText = Gensim_remove_stopwords(text)
				# preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
				wordsText = simple_preprocess(cText, max_len=50)
				# feed the caller
				yield TaggedDocument(words=wordsText, tags=dictTags[file])

		print("\nAd hoc files")

		for file in listCorpusAH:
			fd = _Open(file, "r")
			text = fd.read()
			# remove stopwords
			cText = Gensim_remove_stopwords(text)
			# preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
			wordsText = simple_preprocess(cText, max_len=50)
			# feed the caller
			yield TaggedDocument(words=wordsText, tags=dictTags[file])

		endTime = datetime.now()
		elapsedTime = endTime - startTime
		print(" Duración:", elapsedTime.seconds)


class MyCorpusGen():
	def __init__(self):
		print("MyCorpusGen init")
		return


	def __iter__(self):
		global numIter
		print("MyCorpusGen iteration", numIter)
		numIter = numIter + 1
		startTime = datetime.now()

		for i,file in enumerate(listGeneric):
			if (i % 100) == 0:
				print(i, end=' ', flush=True)

			with codecs.open(file, 'r', encoding='utf-8', errors='ignore') as fdata:
				text = fdata.read()
				# remove stopwords
				cText = Gensim_remove_stopwords(text)
				# preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
				wordsText = simple_preprocess(cText, max_len=50)
				# feed the caller
				yield TaggedDocument(words=wordsText, tags=dictTags[file])

		endTime = datetime.now()
		elapsedTime = endTime - startTime
		print("\nDuración:", elapsedTime.seconds)



class MyCorpusAH():
	def __init__(self):
		print("MyCorpusAH init")
		return


	def __iter__(self):
		global numIter
		print("MyCorpusAH iteration", numIter)
		numIter = numIter + 1

		for file in listCorpusAH:

			fd = _Open(file, "r")
			text = fd.read()
			# remove stopwords
			cText = Gensim_remove_stopwords(text)
			# preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
			wordsText = simple_preprocess(cText, max_len=50)
			# feed the caller
			yield TaggedDocument(words=wordsText, tags=dictTags[file])





# D2V training hyperparameters
vector_size = 100	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 5	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses
# seed = 1 # Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 0	# Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs1 = 10	# epochs (int, optional) – Number of iterations (epochs) over the corpus
epochs2 = 100

print("Vamos a crear la fuente del corpus")
corpus_data_both = MyCorpusBoth()
corpus_data_gen = MyCorpusGen()
corpus_data_ah = MyCorpusAH()


numIter=0
print("\nVamos con la red")
model = Doc2Vec(vector_size=vector_size, window=window, alpha=alpha, min_alpha=min_alpha, min_count=min_count, dm=distributed_memory)
print("Vamos a construir el vocabulario")
model.build_vocab(corpus_data_both)
#model.build_vocab(corpus_data_gen)

print("Vamos a entrenar con epochs=", epochs1, epochs2, " y vector size=", vector_size)
numIter=0
model.train(corpus_data_gen, total_examples=len(listGeneric), start_alpha=alpha, end_alpha=min_alpha, epochs=epochs1)
numIter=0
model.train(corpus_data_ah, total_examples=sizeAHCorpus, start_alpha=alpha, end_alpha=min_alpha, epochs=epochs2)
model.save(MODEL_NAME)
print("Terminado", MODEL_NAME, epochs1, epochs2, "epochs, vector size=", vector_size)
