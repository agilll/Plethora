# the inference of a candidate text in a D2V model is not deterministic, it slightly changes from call to call
# So the positions of the initial text entities change in every execution, and so the average

# to compute such data for a given D2V model, we will run several times (5) the procedure and compute the average

# this is the task of this standalone script, run the procedure 5 textSimilarities
# each time the positions will be computed, and the average
# the final postion for every entity is the average of the the 5 runs


import os
import sys
sys.path.append('../')

from textSimilarities import Doc2VecSimilarity as _Doc2VecSimilarity
from aux_build import SortTuplaList_byPosInTupla as _SortTuplaList_byPosInTupla

HOME = os.getenv('HOME')

# select the model with or withput stopwords. WARNING: textsimilarities.py preprocessing must be equal than this
_LEE_D2V_MODEL = HOME+"/KORPUS/MODELS/d2v_lee.without_stopwords.model"
# _LEE_D2V_MODEL = HOME+"/KORPUS/MODELS/d2v_lee.with_stopwords.model"
_AP_D2V_MODEL = HOME+"/KORPUS/MODELS/doc2vec.bin"

CURRENT_MODEL = _LEE_D2V_MODEL
#CURRENT_MODEL = _AP_D2V_MODEL

# the folder with teh candidate files
_SCRAPPED_PAGES_FOLDER = HOME+"/KORPUS/SCRAPPED_PAGES/"

# read the initial text
P0_originalTextFilename = HOME+"/KORPUS/1926/1926.ph0.txt"
with open(P0_originalTextFilename, 'r') as fp:
  P0_originalText = fp.read()

# read the list of candidates
listWithWKSBFilename = HOME+"/KORPUS/1926/1926.ph4.listWithWKSB"
with open(listWithWKSBFilename, 'r') as fp:
    listWithWKSB = fp.read().splitlines()

# read the relevant entities in the initial text
entitiesFilename = HOME+"/KORPUS/1926/1926.ph1.en"
with open(entitiesFilename) as fp:	# format    http://dbpedia.org/resource/Title
  listEntitiesOriginalText = fp.read().splitlines()

listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
listEntityFilesOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))



print("Starting D2V executions ")

for x in range(1,5):
    print("Starting execution", str(x));

    listOrdered_Names_Sims = []
    d2vSimilarity = _Doc2VecSimilarity(CURRENT_MODEL, P0_originalText)

    # process all candidates
    for idx, rFileNameCandidate in enumerate(listWithWKSB, start=1):  # format rFileNameCandidate = en.wikipedia.org/wiki..Title.txt
      fileNameCandidate = _SCRAPPED_PAGES_FOLDER+rFileNameCandidate   # format $HOME/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Title.txt
      d2v_sim = d2vSimilarity.doc2VecTextSimilarity(candidate_file=fileNameCandidate)
      listOrdered_Names_Sims.append((rFileNameCandidate, d2v_sim))
      if (idx % 5000) == 0:
        print(idx/5000, end=' ', flush=True)

    print(" All docs evaluated")

    # order the rresults by sim
    _SortTuplaList_byPosInTupla(listOrdered_Names_Sims, 1)
    listOrdered_OnlyNames = list(map(lambda x: x[0], listOrdered_Names_Sims))  # keep only the candidates

    originalEntitiesPositions = []
    # search the entities of the initial text
    for idx, name in enumerate(listOrdered_OnlyNames, start=1):
      if name in listEntityFilesOriginalText:  # one entity of the original text found in list
        originalEntitiesPositions.append(idx)
        print("entity", name, "found in postion", idx)
      if len(originalEntitiesPositions) == len(listEntityFilesOriginalText):  # all entities of the original text have been found in the list
        break

    averagePosition = sum(originalEntitiesPositions) / len(originalEntitiesPositions)  # average position
    print("D2V average for execution", str(x), " =", averagePosition)
