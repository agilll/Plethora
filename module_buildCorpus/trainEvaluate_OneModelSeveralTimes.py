
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

modelTargetNumber = sys.argv[1]

# read the initial text
P0_originalTextFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt"  # to compare similarity of .txt files
with open(P0_originalTextFilename, 'r') as fp:
  P0_originalText = fp.read()

lenOriginalText = len(P0_originalText)


# read the relevant entities in the initial text
entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt.en"
with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
  listEntitiesOriginalText = fp.read().splitlines()

listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
listEntityDocsOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))


lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

EVALUATE = 1000 # the number of candidates to evaluate (they are the number more similar)
SEARCH_ENTITIES = 1000 # the number of candidates to search the entities in

filenameListBestAP =  lengthFolder+str(lenOriginalText)+".ph5-3.simsBest.csv"  # list of (candidate,sim) ordered by best similarity in previous phase
listFull_OrderedAP = []
with open(filenameListBestAP, 'r') as csvFile:
	reader = csv.reader(csvFile, delimiter=' ')
	next(reader)  # to skip header
	for row in reader:
		# row[0]=rDocName, row[1]=sim
		listFull_OrderedAP.append(row[0])
	csvFile.close()

print("Tamaño total candidatos =", len(listFull_OrderedAP))
sizeCorpus = int(len(listFull_OrderedAP) / 100) *  int(modelTargetNumber)
print("Tamaño corpus inicial =", sizeCorpus)

#para entrenar
listDocsOriginalCorpus = listFull_OrderedAP[:sizeCorpus]
#random.shuffle(listDocsOriginalCorpus)
#listDocsOriginalCorpus.reverse()
print("Entrenando con los mejores", len(listDocsOriginalCorpus), "ordenados de peor a mejor")

# para evaluar
listTOP_OrderedAP = listFull_OrderedAP[:EVALUATE]
print("Evaluando con", EVALUATE, "ordenados")
listToTest = listTOP_OrderedAP   # the list to test in this run *******************************************+

ping = int(len(listToTest) / 10) # the number of candidates to echo a ping after



modelBase = "M"+str(modelTargetNumber)   # fichero del modelo Mx inicial

models = {}

# how many times the model is trained/evaluated
for x in range(1,11):
    print("\n\nIteration", x)

	# train a new model
    model = modelBase+"."+str(x)+".model"
    models[model] = {'lpos': {}, 'apos': 0 }

    modelFilename = _MODELS_FOLDER+model
    print("Training", modelFilename, "with", len(listDocsOriginalCorpus), "files")
    listDocsW = list(map(lambda x: lengthFolder+"files_s_p_w/"+x[(1+x.rfind("/")):]+".s.w", listDocsOriginalCorpus))
    r = _buildD2VModelFrom_FileList(listDocsW, modelFilename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

    if (r == 0):
        print("Training success for "+modelFilename+"!!")
    else:
        print("Training failed for "+modelFilename+"!")
        break




    print("\nStarting evaluation for model", modelFilename)

    listOrdered_Names_Sims = []
    d2vSimilarity = _Doc2VecSimilarity(modelFilename, P0_originalText)  # ***** add W to eval .w files

    # process the best candidates to observe where the initial entities are
    print("Evaluating", len(listToTest), "candidates")
    for idx,docCandidate in enumerate(listToTest, start=1):  # format docCandidate = en.wikipedia.org/wiki..Title.txt
        if (idx % ping) == 0:
            print(idx, end=' ', flush=True)

        fileNameCandidate = _SCRAPPED_PAGES_FOLDER+docCandidate   # format SCRAPPED_PAGES_FOLDER/en.wikipedia.org/wiki..Title.txt
        #fileNameCandidateW = _CORPUS_FOLDER+"1926/files_s_p_w/"+docCandidate[1+docCandidate.rfind("/"):]+".s.w"  # to compare .w files

        d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameCandidate) # ****** with W to eval .w files
        listOrdered_Names_Sims.append((docCandidate, d2v_sim))

    print(" All candidate sims computed")

    # order the results by sim
    _SortTuplaList_byPosInTupla(listOrdered_Names_Sims, 1)
    listOrdered_OnlyNames = list(map(lambda x: x[0], listOrdered_Names_Sims))  # keep only the candidates already ordered by sim

    originalEntitiesPositions = []
    # search the entities of the initial text
    for idx,name in enumerate(listOrdered_OnlyNames[:SEARCH_ENTITIES], start=1):
        if name in listEntityDocsOriginalText:  # one entity of the original text found in list
            originalEntitiesPositions.append(idx)
            print("entity", name, "found in position", idx)
            models[model]['lpos'][name] = idx
        if len(originalEntitiesPositions) == len(listEntityDocsOriginalText):  # all entities of the original text have been found in the list
            break
        if idx == len(listOrdered_OnlyNames):
            print("ERROR!!!! alcanzado el final del conjunto sin encontrar todas las entidades")
            exit()


    averagePosition = sum(originalEntitiesPositions) / len(originalEntitiesPositions)  # average position
    print("D2V N average for this execution", "=", averagePosition)
    models[model]['apos'] = averagePosition

print("\n\nComplete results")

for model in models:
    print(model, models[model]['apos'])
    for e in models[model]['lpos']:
        print(e, models[model]['lpos'][e])

for model in models:
    print(model, "N="+str(models[model]['apos']))
