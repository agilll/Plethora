# script to test functions processFile and processFolder in S2_BuildDbpediaInfoFromTexts.py

# This script receives as parameter a file (.s) or a folder and, for each file, it generate other (.s.p) with the entities identified in DB-SL 
# input: a .s file or a folder
#			if folder, it is supposed to be the CORPUS base folder, and folder/files_s_p_w must exist, and all '.s' files in folder/files_s_p_w will be processed
# outputs: several files will be created in folder/files_s_p_w
#			a file with '.s.p' extension for each processed file
#			a .s.p.html file with the entities marked in green
 
# IMPORTANT: the identification of entities in DB-SL is done with parameters 'confidence=0.5' and 'support=1'


import os
import sys

from S2_BuildDbpediaInfoFromTexts import processFile as _processFile, processFolder as _processFolder

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

# process a file, source is a .s file
if os.path.isfile(source):
	ok = _processFile(source, confidence, support)
	if ok == -1:
		print(source, "could not be processed")
	
	
# source is a folder. It must be the base CORPUS folder
# it must exist a files_s_p_w folder inside
# process all '.s' files in source/files_s_p_w
elif os.path.isdir(source):
	ok = _processFolder(source, confidence, support)
	if ok == -1:
		print(source, "could not be processed")
	
else:
	print(source, "not found!")
	exit(-1)