# this script computes the N for a given modelList
# to do that, it evaluates the model for all the files, order them by sim, and search the position of the 10 T0 entities
# the result is the average of the position of such 10 entities in the order

import os
import sys
import csv
import random
sys.path.append('../')

from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, CORPUS_FOLDER as _CORPUS_FOLDER, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER

_AP_D2V_MODEL = "doc2vec.bin"
_HYB_D2V_MODEL = "hibrido.model"

# read the initial text
P0_originalTextFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt"  # to compare similarity of .txt files
with open(P0_originalTextFilename, 'r') as fp:
  P0_originalText = fp.read()

P0_originalTextFilenameW = _CORPUS_FOLDER+"1926/1926.ph1.txt.s.w"   # to compare similarity of .w files
with open(P0_originalTextFilenameW, 'r') as fp:
  P0_originalTextW = fp.read()



# read the list of candidates to evaluate from 1926.ph4.listWithWKSB
listWithWKSBFilename = _CORPUS_FOLDER+"1926/1926.ph4.listWithWKSB"
with open(listWithWKSBFilename, 'r') as fp:
    listWKSB = fp.read().splitlines()

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
listFull_ShuffledAP = list(listFull_OrderedAP)
random.shuffle(listFull_ShuffledAP)

list1000_OrderedAP = listFull_OrderedAP[:1000]

list1000_ShuffledAP = list(list1000_OrderedAP)
random.shuffle(list1000_ShuffledAP)

# the list to test in this run *******************************************+
listToTest = list1000_OrderedAP

ping = int(len(listToTest) / 10) # the number of candidates to echo a ping after


# read the relevant entities in the initial text
entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt.en"
with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
  listEntitiesOriginalText = fp.read().splitlines()

listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
listEntityDocsOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))



print("Starting execution")

models = {}
for x in range(1,14):
    model = "M2.model_"+str(x)
    #model = "1926-w."+str(x)+".model"
    #model = "1926-w.2.model"+str(x)
    models[model] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}

#models = {}
#models[_HYB_D2V_MODEL] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
#models[_AP_D2V_MODEL] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
#models["M2.model"] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
#models["1926-w.2.model"] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}

for model in models:
    print("\nStarting execution for model", model)
    CURRENT_MODEL = _MODELS_FOLDER+model

    listOrdered_Names_Sims = []
    d2vSimilarity = _Doc2VecSimilarity(CURRENT_MODEL, P0_originalText)  # ***** add W to eval .w files

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
    for idx,name in enumerate(listOrdered_OnlyNames, start=1):
        if name in listEntityDocsOriginalText:  # one entity of the original text found in list
            originalEntitiesPositions.append(idx)
            print("entity", name, "found in position", idx)
            models[model]['lpos'][name] = idx
        if len(originalEntitiesPositions) == len(listEntityDocsOriginalText):  # all entities of the original text have been found in the list
            break
        if idx == len(listOrdered_OnlyNames):
            print("ERROR!!!! alcanzado el final del conjunto sin encontrar todas las entidades")


    averagePosition = sum(originalEntitiesPositions) / len(originalEntitiesPositions)  # average position
    print("D2V N average for this execution", "=", averagePosition)
    models[model]['apos'] = averagePosition

    d2v_sim = 0
    for e in listEntityDocsOriginalText:
        fileNameEntity = _SCRAPPED_PAGES_FOLDER+e
        #fileNameEntityW = _CORPUS_FOLDER+"1926/files_s_p_w/"+fileNameEntity[1+fileNameEntity.rfind("/"):]+".s.w"  # to compare .w files
        new_d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameEntity)  # ****** with W to eval .w files
        models[model]['lsims'][e] = new_d2v_sim
        d2v_sim += new_d2v_sim

    averageEntitySim = d2v_sim / len(listEntityDocsOriginalText)
    print("D2V Entity SIM average for this execution", "=", averageEntitySim)
    models[model]['asim'] = averageEntitySim



print("\n\nComplete results")

for model in models:
    print(model, models[model]['apos'], models[model]['asim'])
    for e in models[model]['lpos']:
        print(e, models[model]['lpos'][e], models[model]['lsims'][e])

for model in models:
    print(model, "N=", models[model]['apos'])
