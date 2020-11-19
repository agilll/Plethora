# training Doc2Vec models with .w files (preprocessed .txt files, but still text files)

import os
import collections
import glob
import csv
from smart_open import open as _Open
from datetime import datetime
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.parsing.preprocessing import remove_stopwords as Gensim_remove_stopwords
from gensim.utils import simple_preprocess

GEN_FOLDER = "/Users/agil/Downloads/webbase_all/"
MODEL_NAME = "/Users/agil/CloudStation/KORPUS/hibrido.model"
AH_CORPUS_FOLDER = "/Users/agil/CloudStation/KORPUS/SCRAPPED_PAGES/"

# read the list of ad hoc candidates to evaluate from 1926.ph5-3.simsBest.csv

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

sizeAHCorpus = int(len(listAP) / 100) *  8   # 6% of the total candidates
listCorpusAH = listAP[:sizeAHCorpus]

listGeneric = []
dictTags = {}

if not os.path.exists(GEN_FOLDER):
	print(GEN_FOLDER, "not found!")
	quit()
else:
	listGeneric = glob.glob(GEN_FOLDER+"*.txt")	# Get all .txt files in the generic training corpus
	for idx1,doc in enumerate(listGeneric):
		dictTags[doc] = [idx1]
	for idx2,doc in enumerate(listCorpusAH, start=idx1+1):
		dictTags[doc] = [idx2]


class MyCorpusBoth():
	def __init__(self):
		print("MyCorpusBoth init")
		return


	def __iter__(self):
		print("MyCorpusBoth iteration")

		print("epoch generic files")
		startTime = datetime.now()
		for i,file in enumerate(listGeneric):
			if (i % 100) == 0:
				print(i, end=' ', flush=True)

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


		print("epoch ad hoc files")
		for file in listCorpusAH:

			fd = _Open(file, "r")
			text = fd.read()
			# remove stopwords
			cText = Gensim_remove_stopwords(text)
			# preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
			wordsText = simple_preprocess(cText, max_len=50)
			# feed the caller
			yield TaggedDocument(words=wordsText, tags=dictTags[file])



class MyCorpusGen():
	def __init__(self):
		print("MyCorpusGen init")
		return


	def __iter__(self):
		print("MyCorpusGen iteration")

		startTime = datetime.now()
		for i,file in enumerate(listGeneric):
			if (i % 100) == 0:
				print(i, end=' ', flush=True)

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



class MyCorpusAH():
	def __init__(self):
		print("MyCorpusAH init")
		return


	def __iter__(self):
		print("MyCorpusAH iteration")

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
vector_size = 20	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 8	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses
# seed = 1 # Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 1	# Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs = 20	# epochs (int, optional) – Number of iterations (epochs) over the corpus

print("Vamos a crear la fuente del corpus")
corpus_data_both = MyCorpusBoth()
corpus_data_gen = MyCorpusGen()
corpus_data_ah = MyCorpusAH()


print("Vamos con la red")
model = Doc2Vec(vector_size=vector_size, window=window, alpha=alpha, min_alpha=min_alpha, min_count=min_count, dm=distributed_memory)
print("Vamos a construir el vocabulario")
model.build_vocab(corpus_data_gen)
print("Vamos a entrenar")
model.train(corpus_data_gen, total_examples=model.corpus_count, start_alpha=alpha, end_alpha=min_alpha, epochs=epochs)  # hay 408 docs txt en el corpus gen
#model.train(corpus_data_ah, total_examples=5035, start_alpha=alpha, end_alpha=min_alpha, epochs=epochs)  # hay 5035 docs txt en el corpus ah
print("Todo bien, guardamos el modelo")
model.save(MODEL_NAME)



# Model assessment with the training dataset

# quality check 1: compute 1-ranks to show the percentage of cases where each document is the most similar to itself (ideally should be 100%)
# ranks = []
# print("Checking quality #1 of:", model_name)
# print("Computing ranks")
# r1 = 0
# for doc_index in range(len(tagged_training_lists)):  	# Go through each tagged document of the training corpus
# 	if (doc_index % 1000) == 0:
# 		print(doc_index, end=' ', flush=True)
# 	# tagged_training_lists[doc_index].tags = [doc_index]
# 	inferred_vector = model.infer_vector(tagged_training_lists[doc_index].words)  # Infer a new vector for each document of the training corpus
# 	list_more_similar_docs = model.docvecs.most_similar([inferred_vector], topn=len(model.docvecs)) # get the docs most similar to it
# 	rankList = [docindex for docindex,sim in list_more_similar_docs]
# 	rank = rankList.index(doc_index)   # get its rank, ideally should be 1
# 	if doc_index == rankList[0]:
# 		r1 += 1
# 	ranks.append(rank)
#
# print("r1 =", r1/len(tagged_training_lists))
# # Count how many times each document ranks with respect to the training corpus
# documents_ranks = collections.Counter(ranks)
# print(model_name, "ranks[0] =", documents_ranks[0])
