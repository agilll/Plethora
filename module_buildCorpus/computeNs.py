# this script computes the N for a list of models
# to do that, it evaluates the model for the first EVALUATE files, order them by sim, and search the position of the 10 T0 entities
# the result is the average of the position of such 10 entities in the order


EVALUATE  = 1000 # the number of candidates to evaluate (they are the number more similar)
SEARCH_ENTITIES = 1000 # the number of candidates to search the entities in

import os
import sys
import csv
import random
sys.path.append('../')

from computeN import computeN as _computeN
from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, CORPUS_FOLDER as _CORPUS_FOLDER, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER

_AP_D2V_MODEL = "doc2vec.bin"
_HYB_D2V_MODEL = "hibrido.model"


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

# different lists

listTOP_OrderedAP = listFull_OrderedAP[:EVALUATE]

listToTest = listFull_OrderedAP

print("Starting evaluation")

listModels = []
for x in range(1,2):
    #modelFilename = "M5.model_"+str(x)
    #modelFilename = "1926-w."+str(x)+".model"
    #model = "1926-w.2.model"+str(x)
    #models[_HYB_D2V_MODEL] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
    #models["M1.model"] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
    #models["1926-w.2.model"] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}

    listModels.append("M"+str(x)+".model")

#listModels.append(_AP_D2V_MODEL)

models = {}
for m in listModels:
    models[m]  = _computeN(m, listToTest)


print("\n\nComplete results")

for modelFilename in models:
    print("Model=", modelFilename, "N=", models[modelFilename]['avgPos'])
    for e in models[modelFilename]['lPos']:
        print(e, models[modelFilename]['lPos'][e])
