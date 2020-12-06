# parte del modelo M5
# evalua todos y los ordena, se queda con el 5%
# entrena un nuevo modelo con ese 5%
# y vuelta a empezar, en cada iteracion un nuevo modelo

modelTargetNumber = 1

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


# read the relevant entities in the initial text
entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt.en"
with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
  listEntitiesOriginalText = fp.read().splitlines()

listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
listEntityDocsOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))



filenameListBestAP =  lengthFolder+str(lenOriginalText)+".ph5-3.simsBest.csv"  # list of (candidate,sim) ordered by best similarity in previous phase
listFull_OrderedAP = []
simsAP={}
with open(filenameListBestAP, 'r') as csvFile:
    reader = csv.reader(csvFile, delimiter=' ')
    next(reader)  # to skip header
    for row in reader:
        # row[0]=rDocName, row[1]=sim
        listFull_OrderedAP.append(row[0])
        simsAP[row[0]] = row[1]
    csvFile.close()

lenListFull_OrderedAP = len(listFull_OrderedAP)
print("Tamaño total candidatos =", lenListFull_OrderedAP)
sizeCorpus = int(lenListFull_OrderedAP / 100) *  modelTargetNumber
print("Tamaño corpus inicial =", sizeCorpus)

listDocsOriginalCorpus = listFull_OrderedAP[:sizeCorpus]

modelBaseFilename = "M"+str(modelTargetNumber)+".model"   # fichero del modelo Mx inicial
modelFilename = modelBaseFilename
modelFullFilename = _MODELS_FOLDER+modelFilename
iterations = 0

listDocsCorpus = list(listDocsOriginalCorpus)
print("corpus de la iteracion 0 = el primer", modelTargetNumber, "% de AP")

while True:
    iterations += 1
    print("\n\nIteration", iterations)

    simsAdHocD2V = {} # dict to compute new AdHoc D2V sims
    print("Reviewing candidates  ("+str(lenListFull_OrderedAP)+" files) with D2V similarity derived from current model:", modelFilename, flush=True)

    d2vSimilarity = _Doc2VecSimilarity(modelFullFilename, P0_originalText)

    for idx,rCandidateFile in enumerate(listFull_OrderedAP, start=1):    # TIEMPO !!!!!!
    	if (idx % 2000) == 0:
    		print(int(idx/2000), end=' ', flush=True)

    	candidateFile = _SCRAPPED_PAGES_FOLDER+rCandidateFile
    	candidateTextFD = open(candidateFile, "r")
    	candidateText = candidateTextFD.read()
    	simsAdHocD2V[rCandidateFile] = d2vSimilarity.doc2VecTextSimilarity(candidate_text=candidateText)

    print("Candidates reviewed")

    listOrdered = [ (doc, simsAdHocD2V[doc]) for doc in simsAdHocD2V]
    _SortTuplaList_byPosInTupla(listOrdered, 1)  # order sims list by ad hoc d2v similarity
    listOrdered_OnlyNames = [doc for (doc, sim) in listOrdered]   # keep only the names of the docs

    # compute N
    SEARCH_ENTITIES = 1000 # the number of candidates to search the entities in
    originalEntitiesPositions = []
    # search the entities of the initial text
    for idx,name in enumerate(listOrdered_OnlyNames[:SEARCH_ENTITIES], start=1):
        if name in listEntityDocsOriginalText:  # one entity of the original text found in list
            originalEntitiesPositions.append(idx)
            print("entity", name, "found in position", idx)
        if len(originalEntitiesPositions) == len(listEntityDocsOriginalText):  # all entities of the original text have been found in the list
            break
        if idx == len(listOrdered_OnlyNames):
            print("ERROR!!!! alcanzado el final del conjunto sin encontrar todas las entidades")

    averagePosition = sum(originalEntitiesPositions) / len(originalEntitiesPositions)  # average position
    print("D2V N average for this execution", "=", averagePosition)



    max=0
    media=0
    for doc in listDocsCorpus:
        pos = listOrdered_OnlyNames.index(doc)
        media += pos
        if pos > max:
            max = pos

    media = media/len(listDocsCorpus)

	# save data in csv file
    with open("order_eval_"+modelFilename+".csv", 'w') as csvFile:
        fieldnames = ['Doc', 'POS_ap', 'SIM_ap', 'POS_new', 'SIM_new']	# Name columns
        writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
        writer.writeheader()	# Write the column headers

        writer = csv.writer(csvFile, delimiter=' ')
        for idx,pair in enumerate(listOrdered):
            doc = pair[0]
            sim = pair[1]
            try:
                writer.writerow([doc, listFull_OrderedAP.index(doc), simsAP[doc],  idx, sim])
            except Exception as e:
                print("Error writing csv with new similarities ("+str(e)+")")

        csvFile.close()



    newCorpus = listOrdered_OnlyNames[:max]
    print("Última posición de un miembro del corpus anterior en el nuevo ordenamiento=", max)
    print("Posición media de un miembro del corpus anterior en el nuevo ordenamiento=", media)

    print("Longitud del nuevo corpus=", len(newCorpus))
    listDocsCorpus = list(newCorpus)




    # nuevos=0
    # for doc in listOrdered_OnlyNames:
    #     if not doc in listDocsCorpus:
    #         listDocsCorpus.append(doc)
    #         nuevos += 1
    #     if nuevos == 10:
    #         break
    # print("Le añado 10 nuevos")

	# train a new model
    modelFilename = modelBaseFilename+"_"+str(iterations)
    modelFullFilename = _MODELS_FOLDER+modelFilename

    print("Training", modelFilename, "with", len(listDocsCorpus), "files")
    listDocsW = list(map(lambda x: lengthFolder+"files_s_p_w/"+x[(1+x.rfind("/")):]+".s.w", listDocsCorpus))

    r = _buildD2VModelFrom_FileList(listDocsW, modelFullFilename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

    if (r == 0):
        print("Training success for "+modelFilename+"!!")
    else:
        print("Training failed for "+modelFilename+"!")
