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

if len(sys.argv) < 3:
	print("Use: "+sys.argv[0]+" EVALUATE  num_modelo")
	exit(-1)

EVALUATE  = int(sys.argv[1])   # the number of candidates to evaluate (they are the number more similar)
num = sys.argv[2]


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
            listFull_OrderedAP.append(row[0])  # read only the name of the doc # format en.wikipedia.org/wiki..Title.txt
        csvFile.close()
except Exception as e:
    print("Exception reading csv file:", filenameListBestAP, str(e))
    sys.exit()

# listFull_OrderedAP for everyone, listTOP_OrderedAP for teh first 1000
listTOP_OrderedAP = listFull_OrderedAP[:EVALUATE]
listToTest = listTOP_OrderedAP

print("Starting evaluation: ", EVALUATE, num)

listModels = [] # the list of models to evaluate
#listModels.append(_AP_D2V_MODEL)
prefix="hib"
listModels.append(prefix+num+"/"+_HYB_D2V_MODEL)

# eval all models
models = {}
for m in listModels:
    models[m]  = _computeN(m, listToTest)

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
