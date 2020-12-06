# this script computes the N for a list of models
# to do that, it evaluates the model for the first EVALUATE files, order them by sim, and search the position of the 10 T0 entities
# the result is the average of the position of such 10 entities in the order

import os
import sys
import csv
import random
from datetime import datetime

sys.path.append('../')

from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, CORPUS_FOLDER as _CORPUS_FOLDER, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER

EVALUATE  = 1000 # the number of candidates to evaluate (they are the number more similar)
SEARCH_ENTITIES = 1000 # the number of candidates to search the entities in

def computeN (modelFilename, listToTest):
    print("\nStarting evaluation for model", modelFilename)
    ping = int(len(listToTest) / 10) # the number of candidates to echo a ping after
    CURRENT_MODEL = _MODELS_FOLDER+modelFilename

    model = {'lPos': {}, 'avgPos': 0}

    # read the initial text
    P0_originalTextFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt"  # to compare similarity of .txt files
    with open(P0_originalTextFilename, 'r') as fp:
        P0_originalText = fp.read()



    listOrdered_Names_Sims = []
    d2vSimilarity = _Doc2VecSimilarity(CURRENT_MODEL, P0_originalText)

    startTime = datetime.now()
    # process the best candidates to observe where the initial entities are
    print("Evaluating", len(listToTest), "candidates")
    for idx,docCandidate in enumerate(listToTest, start=1):  # format docCandidate = en.wikipedia.org/wiki..Title.txt
        if (idx % ping) == 0:
            print(idx, end=' ', flush=True)

        fileNameCandidate = _SCRAPPED_PAGES_FOLDER+docCandidate   # format SCRAPPED_PAGES_FOLDER/en.wikipedia.org/wiki..Title.txt
        d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameCandidate) # ****** with W to eval .w files
        listOrdered_Names_Sims.append((docCandidate, d2v_sim))

    print(" All candidate sims computed")
    endTime = datetime.now()
    elapsedTime = endTime - startTime
    print("Tardó = ", elapsedTime.seconds)

    # order the results by sim
    _SortTuplaList_byPosInTupla(listOrdered_Names_Sims, 1)
    listOrdered_OnlyNames = [doc for (doc,sim) in listOrdered_Names_Sims]  # keep only the candidates, already ordered by sim


    # read the relevant entities in the initial text
    entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt.en"
    with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
        listEntitiesOriginalText = fp.read().splitlines()

    listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
    # add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
    listEntityDocsOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))



    originalEntitiesPositions = []
    # search the entities of the initial text
    for idx,name in enumerate(listOrdered_OnlyNames[:SEARCH_ENTITIES], start=1):
        if name in listEntityDocsOriginalText:  # one entity of the original text found in list
            originalEntitiesPositions.append(idx)
            model['lPos'][name] = idx
        if len(originalEntitiesPositions) == len(listEntityDocsOriginalText):  # all entities of the original text have been found in the list
            break
        if idx == len(listOrdered_OnlyNames):
            print("ERROR!!!! alcanzado el final del conjunto sin encontrar todas las entidades")


    averagePosition = sum(originalEntitiesPositions) / len(originalEntitiesPositions)  # average position
    print("N=", averagePosition)
    model['avgPos'] = averagePosition

    return model
