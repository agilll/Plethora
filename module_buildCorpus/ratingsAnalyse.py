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

results = {}

# read the list of ratings
resultsFilename = "ratingsResults.csv"

with open(resultsFilename, 'r') as csvFile:
    reader = csv.reader(csvFile, delimiter=' ')
    next(reader)  # to skip header
    for row in reader:
        run = row[0]
        if not run in results:
            results[run]={}
        model = row[1]
        if not model in results[run]:
            results[run][model]={}
        entity = row[2]
        if not entity in results[run][model]:
            results[run][model][entity]=(0,0)
        position = row[3]
        sim = row[4]

        results[run][model][entity] = (int(position), float(sim))
    modelList = [model for model in results['1']]
    csvFile.close()



print("\nmedias de todos los modelos para cada run")
for run in results:
    for model in results[run]:
        listaPos = [results[run][model][entity][0] for entity in results[run][model]]
        listaSim = [results[run][model][entity][1] for entity in results[run][model]]

        mediaPos = sum(listaPos)/len(listaPos)
        mediaSim = sum(listaSim)/len(listaSim)

        listaPos.remove(max(listaPos))
        listaSim.remove(max(listaSim))

        mediaPosSinMax = sum(listaPos)/len(listaPos)
        mediaSimSinMax = sum(listaSim)/len(listaSim)

        print(run+"."+model, round(mediaPos,1), round(mediaSim,3), round(mediaPosSinMax,1), round(mediaSimSinMax,3))


print("\nmedia en todos los runs de cada modelo")

models = {}    #  models[m] = {'sumaAvgPos': float, 'sumaAvgSim': float}   los 15 modelos
for run in results:
    for model in results[run]:
        if not model in models:
            models[model]= {'lpos': [], 'lsim': []}
        for entity in results[run][model]:
            models[model]['lpos'].append(results[run][model][entity][0])
            models[model]['lsim'].append(results[run][model][entity][1])

for model in models:
    avgPos = sum(models[model]['lpos']) / len(models[model]['lpos'])
    avgSim = sum(models[model]['lsim']) / len(models[model]['lsim'])

    models[model]['lpos'].remove(max(models[model]['lpos']))
    models[model]['lsim'].remove(max(models[model]['lsim']))

    avgPosSinMax = sum(models[model]['lpos']) / len(models[model]['lpos'])
    avgSimSinMax = sum(models[model]['lsim']) / len(models[model]['lsim'])

    print(model, round(avgPos,1), round(avgSim,3), round(avgPosSinMax,1), round(avgSimSinMax,3))
