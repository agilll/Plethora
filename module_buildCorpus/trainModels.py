
# entrena un nuevo modelo con el mejor x%  de best SIM
# y vuelta a empezar, en cada iteracion un nuevo modelo

import sys
import os
import csv
import random

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


filenameListBestAP =  lengthFolder+str(lenOriginalText)+".ph5-3.simsBest.csv"  # list of (candidate,sim) ordered by best similarity in previous phase
listFull_OrderedAP = []
with open(filenameListBestAP, 'r') as csvFile:
	reader = csv.reader(csvFile, delimiter=' ')
	next(reader)  # to skip header
	for row in reader:
		# row[0]=rDocName, row[1]=sim
		listFull_OrderedAP.append(row[0])
	csvFile.close()

lenListFull_OrderedAP = len(listFull_OrderedAP)
print("Tamaño total candidatos =", lenListFull_OrderedAP)
sizeCorpus = int(lenListFull_OrderedAP / 100) *  modelTargetNumber
print("Tamaño corpus inicial =", sizeCorpus)

listDocsOriginalCorpus = listFull_OrderedAP[:sizeCorpus]

modelBaseFilename = _MODELS_FOLDER+"M1.model"   # fichero del modelo Mx inicial
modelFilename = modelBaseFilename
iterations = 0


listDocsCorpus = listDocsOriginalCorpus
while True:
    iterations += 1
    print("\n\nIteration", iterations)

	# train a new model
    modelFilename = modelBaseFilename+"_"+str(iterations)

    print("Training", modelFilename, "with", len(listDocsCorpus), "files")
    listDocsW = list(map(lambda x: lengthFolder+"files_s_p_w/"+x[(1+x.rfind("/")):]+".s.w", listDocsCorpus))
    random.shuffle(listDocsW)
    r = _buildD2VModelFrom_FileList(listDocsW, modelFilename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

    if (r == 0):
        print("Training success for "+modelFilename+"!!")
    else:
        print("Training failed for "+modelFilename+"!")
        break
