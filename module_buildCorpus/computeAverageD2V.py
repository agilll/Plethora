# the inference of a candidate text in a D2V model is not deterministic, it slightly changes from call to call to the script that computes it
# So the positions of the initial text entities change in every execution, and so the average

# to compute such data for a given D2V model, we will run several times (5) the procedure and compute the average

# this is the task of this standalone script, run the procedure once to compute the positions
# we will run this script 5 times and the final postion for every entity will be the average of the the 5 runs
# we cannot inclue a 5 times loop in this script, as the seed will be the same and so the results (why?)

# this script is intended to be executed after the phase 5 of the global algorithm, to complete the results with the D2V data


import os
import sys
import csv
import random
sys.path.append('../')

from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, CORPUS_FOLDER as _CORPUS_FOLDER

_AP_D2V_MODEL = "doc2vec.bin"
_HYB_D2V_MODEL = "hibrido.model"

# the folder with teh candidate files
_SCRAPPED_PAGES_FOLDER = _CORPUS_FOLDER+"SCRAPPED_PAGES/"

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
listBestAPFilename = _CORPUS_FOLDER+"1926/1926.ph5-3.simsBest.csv"
listAP = []

try:
    with open(listBestAPFilename, 'r') as csvFile:
        reader = csv.reader(csvFile, delimiter=' ')
        next(reader)  # to skip header
        for row in reader:
            listAP.append(row[0])
        csvFile.close()
except Exception as e:
    print("Exception reading csvFile:", listBestAPFilename, str(e))

listToTest = listAP[:1000]  # listWKSB  o   listAP[:1000]
ping = int(len(listToTest) / 20) # the number of candidates to echo a ping after

# listToTest.reverse()          # just to test influence
# random.shuffle(listToTest)

# read the relevant entities in the initial text
entitiesFilename = _CORPUS_FOLDER+"1926/1926.ph1.txt.en"
with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
  listEntitiesOriginalText = fp.read().splitlines()

listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
listEntityFilesOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))

print("Starting execution")

models = {}
for x in range(1,11):
    #model = "1926-w.8.model"+str(x)
    model = "1926-w."+str(x)+".model"
    models[model] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}

models = {}
#models[_AP_D2V_MODEL] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
models[_HYB_D2V_MODEL] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}
#models["1926-w.8.model"] = {'lpos': {}, 'lsims': {}, 'apos': 0, 'asim': 0}

for model in models:
    print("\nStarting execution for model", model)
    CURRENT_MODEL = _MODELS_FOLDER+model

    listOrdered_Names_Sims = []
    d2vSimilarity = _Doc2VecSimilarity(CURRENT_MODEL, P0_originalText)  # ***** with W to eval .w files

    # process the best candidates to observe where the initial entities are
    for idx,rFileNameCandidate in enumerate(listToTest, start=1):  # format rFileNameCandidate = en.wikipedia.org/wiki..Title.txt
        if (idx % ping) == 0:
            print(idx, end=' ', flush=True)

        fileNameCandidate = _SCRAPPED_PAGES_FOLDER+rFileNameCandidate   # format CORPUS_FOLDER/SCRAPPED_PAGES/en.wikipedia.org/wiki..Title.txt

        fileNameCandidateW = _CORPUS_FOLDER+"1926/files_s_p_w/"+rFileNameCandidate[1+rFileNameCandidate.rfind("/"):]+".s.w"  # to compare .w files

        d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameCandidate) # ****** with W to eval .w files
        listOrdered_Names_Sims.append((rFileNameCandidate, d2v_sim))

    print(" All candidate sims computed")

    # order the results by sim
    _SortTuplaList_byPosInTupla(listOrdered_Names_Sims, 1)
    listOrdered_OnlyNames = list(map(lambda x: x[0], listOrdered_Names_Sims))  # keep only the candidates already ordered by sim

    originalEntitiesPositions = []
    # search the entities of the initial text
    for idx, name in enumerate(listOrdered_OnlyNames, start=1):
        if name in listEntityFilesOriginalText:  # one entity of the original text found in list
            originalEntitiesPositions.append(idx)
            print("entity", name, "found in position", idx)
            models[model]['lpos'][name] = idx
        if len(originalEntitiesPositions) == len(listEntityFilesOriginalText):  # all entities of the original text have been found in the list
            break
        if idx == len(listOrdered_OnlyNames):
            print("ERROR!!!! alcanzado el final del conjunto sin encontrar todas las entidades")


    averagePosition = sum(originalEntitiesPositions) / len(originalEntitiesPositions)  # average position
    print("D2V N average for this execution", " =", averagePosition)
    models[model]['apos'] = averagePosition

    d2v_sim = 0
    for e in listEntityFilesOriginalText:
        fileNameEntity = _SCRAPPED_PAGES_FOLDER+e
        fileNameEntityW = _CORPUS_FOLDER+"1926/files_s_p_w/"+fileNameEntity[1+fileNameEntity.rfind("/"):]+".s.w"  # to compare .w files
        new_d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameEntity)  # ****** with W to eval .w files
        models[model]['lsims'][e] = new_d2v_sim
        d2v_sim += new_d2v_sim

    averageEntitySim = d2v_sim / len(listEntityFilesOriginalText)
    print("D2V Entity SIM average for this execution", "=", averageEntitySim)
    models[model]['asim'] = averageEntitySim


print("Complete results")

for model in models:
    print(model, models[model]['apos'], models[model]['asim'])
    for e in models[model]['lpos']:
        print(e, models[model]['lpos'][e], models[model]['lsims'][e])
