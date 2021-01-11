# this script computes the N for a model
# to do that, it evaluates the model for the received files, order them by sim, and search the position of the 10 T0 entities
# the result is the average of the position of such 10 entities in the order

import os
import sys
import csv
import random
import statistics
from datetime import datetime
from smart_open import open as _Open
#sys.path.append('../')

from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, CORPUS_FOLDER as _CORPUS_FOLDER, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER

def checkOutliar(lista):
    from numpy import percentile
    from numpy import mean
    from numpy import std

    outliarZ=False
    outliarIRQ=False

	# identify IRQ outliers
    q25, q75 = percentile(lista, 25), percentile(lista, 75)
    iqr = q75 - q25
    cut_off = iqr * 1.5
    lower, upper = q25 - cut_off, q75 + cut_off

    for pos in lista:
        if (pos < lower) or (pos > upper):
            print("IQR Outliar in", pos)
            outliarIRQ=True
            break

	# identify Z-score outliers
    mean, std = mean(lista), std(lista)
    cut_off = std * 3
    lower, upper = mean - cut_off, mean + cut_off

    for pos in lista:
        if (pos < lower) or (pos > upper):
            print("Z-score Outliar in", pos)
            outliarZ=True
            break

    return (outliarIRQ and outliarZ)


def computeN (modelFilename, listToTest):
    print("\nStarting evaluation for model", modelFilename)
    ping = int(len(listToTest) / 10) # the number of candidates to echo a ping after
    CURRENT_MODEL = _MODELS_FOLDER+modelFilename

    # read the initial text
    P0_originalTextFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt"  # to compare similarity with .txt files
    with open(P0_originalTextFilename, 'r') as fp:
        P0_originalText = fp.read()

    listOrdered_Names_Sims = []
    d2vSimilarity = _Doc2VecSimilarity(CURRENT_MODEL, P0_originalText)

    startTime = datetime.now()
    print("Evaluating", len(listToTest), "candidates")
    sims = {}
    for idx,docCandidate in enumerate(listToTest, start=1):  # format docCandidate = en.wikipedia.org/wiki..Title.txt
        if (idx % ping) == 0:
            print(idx, end=' ', flush=True)

        fileNameCandidate = _SCRAPPED_PAGES_FOLDER+docCandidate   # format SCRAPPED_PAGES_FOLDER/en.wikipedia.org/wiki..Title.txt
        d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameCandidate)
        sims[docCandidate] = d2v_sim
        listOrdered_Names_Sims.append((docCandidate, d2v_sim))

    print(" All candidate sims computed")
    endTime = datetime.now()
    elapsedTime = endTime - startTime
    print("Tardó = ", elapsedTime.seconds)

    # order the results by sim
    _SortTuplaList_byPosInTupla(listOrdered_Names_Sims, 1)
    listOrdered_OnlyNames = [doc for (doc,sim) in listOrdered_Names_Sims]  # keep only the candidates, already ordered by sim


    # # store all ordered results for this model
    # with _Open(CURRENT_MODEL+".csv", 'w') as csvFile:
    #     fieldnames = [modelFilename, "D2V"]	# Name columns
    #     writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
    #     writer.writeheader()	# Write the column headers
    #
    #     writer = csv.writer(csvFile, delimiter=' ')
    #     for row in listOrdered_Names_Sims:
    #         try:
    #             writer.writerow([row[0], row[1]])   # store (doc, sim)
    #         except:
    #             print("Error writing csv with sims for", modelFilename, row)
    #             _appendFile(logFilename, "Error writing csv with sims for"+str(row))
    #
    #     csvFile.close()



    # read the relevant entities in the initial text
    entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph6.txt.en"
    with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
        listEntitiesOriginalText = fp.read().splitlines()

    listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
    # add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
    listEntityDocsOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))

    model = {} # to store results    model[doc] = (pos, sim)

    # search the entities of the initial text
    originalEntitiesPositions = []
    for idx,docCandidate in enumerate(listOrdered_OnlyNames, start=1):
        if docCandidate in listEntityDocsOriginalText:  # one entity of the original text found in list
            print("Found", docCandidate, "--- pos=", idx, "--- sim=", round(sims[docCandidate],3))
            if len(originalEntitiesPositions) > 8: # this is the 9th, let's start to check for outliars
                newlist = list(originalEntitiesPositions)
                newlist.append(idx) # add the new one
                if checkOutliar(newlist):
                    print("Found outliar", ":", docCandidate, idx)
                    break # to discard the outliar, here we don't do it
            originalEntitiesPositions.append(idx)
            model[docCandidate] = (idx,sims[docCandidate])

        if len(originalEntitiesPositions) == len(listEntityDocsOriginalText):  # all entities of the original text have been found in the list
            break
        if idx == len(listOrdered_OnlyNames):
            print("ERROR!!!! alcanzado el final del conjunto sin encontrar todas las entidades")


    positions = [model[entity][0] for entity in model]  # the idx for every candidate found
    media = statistics.mean(positions)  # full average position
    print("N =", round(media,1))

    return model
