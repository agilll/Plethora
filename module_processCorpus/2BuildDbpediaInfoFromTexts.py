#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script receives as parameter a file (.s) or a folder and, for each file, it generate other (.s.p) with the entities identified in DB-SL 
# input: a .s file or a folder
#			if folder, it is supposed to be the CORPUS base folder, and folder/files_s_p_w must exist, and all '.s' files in folder/files_s_p_w will be processed
# outputs: several files will be created in folder/files_s_p_w
#			a file with '.s.p' extension for each processed file
#			a .s.p.html file with the entities marked in green
 
# IMPORTANT: the identification of entities in DB-SL is done with parameters 'confidence=0.5' and 'support=1'

# select ?uri ?label (group_concat(?subject; separator=";") as ?subjects) (group_concat(?type; separator=";") as ?types)
# where {

# VALUES ?uri {<http://dbpedia.org/resource/Hera> <http://dbpedia.org/resource/Eurotas> <http://dbpedia.org/resource/Dodona> <http://dbpedia.org/resource/Determinism> <http://dbpedia.org/resource/Julius_Caesar>} .
# ?uri rdfs:label ?label; rdf:type ?type .
# ?uri dct:subject ?subject .
# FILTER(regex(?type,'http://dbpedia.org/ontology|http://dbpedia.org/class/yago')) . FILTER(lang(?label) = 'en')} group by ?label ?uri


import os
import pickle
import json
import requests
import sys
sys.path.append('../')  # to search for imported files in the parent folder


from px_aux import URL_DB_SL_annotate as _URL_DB_SL_annotate, getContentMarked as _getContentMarked, saveFile as _saveFile
from px_DB_Manager import DBManager as _DBManager

from aux import  SPW_FOLDER as _SPW_FOLDER

# to process a file and return dictionaries with the entities detected and filtered 
def findEntities (filename, confPar, supPar):
		
	content_file = open(filename, 'r')
	content = content_file.read()
	
	# DB-SL is queried for teh preferred entity for each candidate detected in the file
	# see section 6.4 of the document describing the architecture for the formats of request and answer 
	dbsl_response = requests.post(_URL_DB_SL_annotate, data={"text": content, "confidence": confPar, "support": supPar}, headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"})
	
	# the previous one is a synchronous call, anly returns after receiving the answer, that will be passed now to JSON
	try:
		dbsl_json = dbsl_response.json()
		dbsl_json["Resources"] # if no entity is detected an exception is raised
	except:
		print("No entity detected in the file")
		return {'byUri': {}, 'byType': {}, 'byOffset': {}}

	print("Detected", len( dbsl_json["Resources"]), "entities")
	
	# create class  _DBManager to parse results
	dbpediaManager = _DBManager()
	dbpediaManager.scanEntities(dbsl_json)
	allDicts = dbpediaManager.getDictionaries()
	
	byUri = allDicts["byUri"]
	byType = allDicts["byType"]
	byOffset = allDicts["byOffset"]
	byuriplana = [item for sublist in byUri.values() for item in sublist]
	print(len(byUri.keys()), len(byuriplana), len(byType.keys()), len(byOffset.keys()))
	
	return allDicts





# start script execution

# parameter checking

# at least a parameter  
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

confidence = 0.5   # default parameters for DB-SL
support = 1

# if one parameter it cannot start by '-'
if len(sys.argv) == 2:
	source = sys.argv[1]

# to simplify,  '-c' and '-s' must go together, or both or none
elif len(sys.argv) == 6:
	if sys.argv[1] == "-c":
		confidence = sys.argv[2]
	elif sys.argv[1] == "-s":
		support = sys.argv[2]
	else:
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
		
	if sys.argv[3] == "-c":
		confidence = sys.argv[4]
	elif sys.argv[3] == "-s":
		support = sys.argv[4]
	else:
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
	
	source = sys.argv[5]   # this is the file|folder with the source data

else:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)
	
	
	
# start processing

print("Processing with Confidence=", confidence, " and Support=", support, "\n")

# process a file, source is the .s global filename
if os.path.isfile(source):
	if source.endswith(".s"):
		print("Processing file "+source+"...\n")
		entities = findEntities(source, confidence, support)
		pickle.dump(entities, open(source+".p", "wb" ))
			
		highlightedContent = _getContentMarked(source, 's')
		_saveFile(source+".p.html", highlightedContent)
	else:
		print("The file "+source+" has not '.s' extension")
		exit(-1)
	
# source is a folder. It must be the base CORPUS folder
# it must exist a files_s_p_w folder inside
# process all '.s' files in source/files_s_p_w
elif os.path.isdir(source):
	print("Processing folder "+source+"...")
	numFiles = 0
	spw_folder = source + _SPW_FOLDER
	if not os.path.exists(spw_folder):
		print(spw_folder, "not found!")
		exit()
	
	for sfilename in sorted(os.listdir(spw_folder)):
		if sfilename.endswith(".s"):
			numFiles += 1
			sfullfilename = spw_folder+sfilename
			print("\n", numFiles, " **************** Processing file ", sfullfilename+"...\n")
			entities = findEntities(sfullfilename, confidence, support)
			pickle.dump(entities, open(sfullfilename+".p", "wb" ))
			
			highlightedContent = _getContentMarked(sfullfilename, "s")
			_saveFile(sfullfilename+".p.html", highlightedContent)
		else:
			continue
	
else:
	print(source, "not found!")
	exit(-1)
	
	

	
	
	
	