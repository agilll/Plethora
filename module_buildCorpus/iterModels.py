# parte del modelo M2


import sys
import os
import csv

sys.path.append('..')
from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import CORPUS_FOLDER as _CORPUS_FOLDER,  SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER, MODELS_FOLDER as _MODELS_FOLDER

from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity


# to train the D2V model
sys.path.append('../module_train')
from D2V_BuildOwnModel_w import buildD2VModelFrom_FileList as _buildD2VModelFrom_FileList

# D2V training hyperparameters
vector_size = 20	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 8	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses
# seed = 1 # Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 1	# Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs = 100	# epochs (int, optional) – Number of iterations (epochs) over the corpus


# read the initial text
P0_originalTextFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt"  # to compare similarity of .txt files
with open(P0_originalTextFilename, 'r') as fp:
  P0_originalText = fp.read()

lenOriginalText = len(P0_originalText)

lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"
modelTargetNumber = 2


# read the list of candidates to evaluate from 1926.ph5-3.simsBest.csv
filenameListBestAP = _CORPUS_FOLDER+"1926/1926.ph5-3.simsBest.csv"
listFull_OrderedAP = []
try:
    with open(filenameListBestAP, 'r') as csvFile:
        reader = csv.reader(csvFile, delimiter=' ')
        next(reader)  # to skip header
        for row in reader:
            listFull_OrderedAP.append(row[0])  # read only the name of the doc
        csvFile.close()
except Exception as e:
    print("Exception reading csv file:", filenameListBestAP, str(e))
    sys.exit()

lenListFull_OrderedAP = len(listFull_OrderedAP)

sizeCorpus = int(lenListFull_OrderedAP / 100) *  modelTargetNumber
print("Tamaño corpus inicial =", sizeCorpus)

listDocsOriginalCorpus = listFull_OrderedAP[0:sizeCorpus]

modelBaseFilename = _MODELS_FOLDER+"M2.model"    # fichero del modelo Mx inicial
modelFilename = modelBaseFilename
iterations = 0


# entrenamos de nuevo M2 con el mismo corpus inicial, generamos M2_0

# generamos los W correspondientes al corpus inicial
listDocsW = list(map(lambda x: lengthFolder+"files_s_p_w/"+x[(1+x.rfind("/")):]+".s.w", listDocsOriginalCorpus))

r = _buildD2VModelFrom_FileList(listDocsW, modelFilename+"_new", vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

if (r == 0):
	print("Training success for "+modelFilename+"_new")
else:
	print("Training failed for "+modelFilename+"_new")

sys.exit()








listDocsCorpus = listDocsOriginalCorpus
while True:
	iterations += 1
	print("\n\nIteration", iterations)

	simsAdHocD2V = {} # dict to compute new AdHoc D2V sims
	print("Reviewing candidates  ("+str(lenListDocs_SimBestSim)+" files) with Doc2Vec similarity derived from current model:", modelFilename, flush=True)

	d2vSimilarity = _Doc2VecSimilarity(modelFilename, P0_originalText)

	for idx,rCandidateFile in enumerate(listDocsBestSim, start=1):
		if (idx % 2000) == 0:
			print(int(idx/2000), end=' ', flush=True)

		candidateFile = _SCRAPPED_PAGES_FOLDER+rCandidateFile
		candidateTextFD = open(candidateFile, "r")
		candidateText = candidateTextFD.read()
		doc2vec_trained_cosineSimilarity = d2vSimilarity.doc2VecTextSimilarity(candidate_text=candidateText)
		simsAdHocD2V[rCandidateFile] = doc2vec_trained_cosineSimilarity

	print("Candidates reviewed")

	listOrdered = [ (k, simsAdHocD2V[k]) for k in simsAdHocD2V]
	_SortTuplaList_byPosInTupla(listOrdered, 1)  # order sims list by ad hoc d2v similarity
	listOrdered_OnlyNames = list(map(lambda x: x[0], listOrdered))  # keep only the names of the docs

	listBest_OnlyNames = listOrdered_OnlyNames[:sizeCorpus]   # mejores x% de acuerdo al modelo Mx

	# le añadimos un fichero al corpus
	for doc in listOrdered_OnlyNames:
		if not doc in listDocsCorpus:
			listDocsCorpus.append(doc)
			break

	# train a new model
	modelFilename = modelBaseFilename+"_"+str(iterations)

	print("Training", modelFilename, "with", len(listDocsCorpus), "files")
	listCorpusFilesGlobalNames = list(map(lambda x: _SCRAPPED_PAGES_FOLDER+x, listDocsCorpus))

	r = _buildD2VModelFrom_FileList(listCorpusFilesGlobalNames, modelFilename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

	if (r == 0):
		print("Training success for "+modelFilename+"!!")
	else:
		print("Training failed for "+modelFilename+"!")
