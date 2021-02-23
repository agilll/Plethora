# this script computes the N for a list of models
# to do that, it evaluates the model for the first EVALUATE files, order them by sim, and search the position of the 10 T0 entities
# the result is the average of the position of such 10 entities in the order

import os
import sys
import csv
import random
import statistics
sys.path.append('../')

from computeN import computeN as _computeN
from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, CORPUS_FOLDER as _CORPUS_FOLDER, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER

if len(sys.argv) < 5:
	print("Use: "+sys.argv[0]+" EVALUATE  num_modelo_inicial  num_modelo_final dir_modelos")
	exit(-1)

EVALUATE  = int(sys.argv[1])   # the number of candidates to evaluate (they are the number more similar)
mini = int(sys.argv[2])
mfin = int(sys.argv[3])
dir_modelos = sys.argv[4]

_AP_D2V_MODEL = "doc2vec.bin"

# read the relevant entities of the initial text that will be searched in the ordered set
entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt.en"    # this is for 18 entities, change to ph1 for 10 entities
with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
    listEntitiesOriginalText = fp.read().splitlines()

listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
listEntityDocsOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))




# read the list of candidates to evaluate from 1926.ph5-3.simsBest.csv
filenameListBestAP = _CORPUS_FOLDER+"1926/1926.ph5-3.simsBest.csv"
listFull_OrderedAP = []
try:
    with open(filenameListBestAP, 'r') as csvFile:
        reader = csv.reader(csvFile, delimiter=' ')
        next(reader)  # to skip header
        for row in reader:
            listFull_OrderedAP.append(row[0])  # read only the name of the doc # format en.wikipedia.org/wiki..Title.txt
        csvFile.close()
except Exception as e:
    print("Exception reading csv file:", filenameListBestAP, str(e))
    sys.exit()

# listFull_OrderedAP for everyone, listTOP_OrderedAP for teh first 1000
listTOP_OrderedAP = listFull_OrderedAP[:EVALUATE]
listToTest = listTOP_OrderedAP
random.shuffle(listToTest)

print("Starting multiple evaluation: ", EVALUATE, mini, mfin, dir_modelos)

listModels = [] # the list of models to evaluate
listModels.append(_AP_D2V_MODEL)
prefix=dir_modelos+"/"
for x in range(mini, mfin):
    #listModels.append("M"+str(x)+".model")
    listModels.append(prefix+"1926-w."+str(x)+".model")

# eval all models
models = {}
for m in listModels:
    models[m]  = _computeN(m, listToTest, listEntityDocsOriginalText)

# get the minimum number without outliars
globalNumber=100
for m in models:
    thisModelNumber=0
    for e in models[m]:
        if models[m][e][2] == False:
            thisModelNumber += 1
    if thisModelNumber <  globalNumber:
        globalNumber = thisModelNumber

print("Numero mínimo a contabilizar para N = ", globalNumber)

# get the averages with such minimum number
for m in models:
    lista = []
    number = 0
    for e in models[m]:
        if number < globalNumber:
            lista.append(models[m][e][0])
            number += 1
        else:
            break

    media = statistics.mean(lista)  # full average position
    print(m, "N =", round(media,1))
