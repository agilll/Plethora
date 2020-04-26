# script to test functions processFile and processFolder in S1_AddSuffixToTexts.py

# input: a file or folder received as parameter
#			if folder, the subfolder folder/files_txt/ must exist, and all '.txt' files in folder/files_txt will be processed
# outputs:	for each processed file, several files will be created 
#			a file with the original name and the suffix '.s', for every processed file
#			a .s.html' file with the changes in green, for every processed file (just to easily read changes)
#           a .s.nr with report about studied changes finally not done (for debugging) 
#           a .s.nr.html with HTML report about studied changes finally not done (for debugging) 

#		In case of the '-g' modifier a new file 'folder/folder.s' will be created aggregating all the created '.s' files in folder/files_s_p_w.

import os
import sys

from S1_AddSuffixToTexts import processS1File as _processS1File, processS1Folder as _processS1Folder


# variable to control if aggregated file must be created     
join = False


# parameter checking

# one parameter is required  
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" [-g] file|folder")
	exit(-1)

# one parameter, it is the file|folder
if len(sys.argv) == 2:
	source = sys.argv[1]
	
# two parameters, the first one must be '-g', the second one is the file|folder
elif len(sys.argv) == 3:
	if sys.argv[1] == "-g":
		join = True
		source = sys.argv[2]
	else:
		print("Use: "+sys.argv[0]+" [-g] file|folder")
		exit(-1)

# more than two parameters is not permitted
else:
	print("Use: "+sys.argv[0]+" [-g] file|folder")
	exit(-1)

	
	
# start processing

# it is a file, it must be the global name of a .txt file
if os.path.isfile(source):
	if not source.endswith(".txt"):
		print("The file "+source+" is not '.txt'")
		exit(-1)
	print("Processing file "+source+"...\n")
	_processS1File(source)
	
# source is a folder. It must be the base CORPUS folder
# it must exist a files_txt folder inside
# all '.txt' files inside folder/files_txt/ are processed 
elif os.path.isdir(source):
	if not os.path.exists(source):
		print(source, "not found!")
		exit()
	print("Processing folder "+source+"...")
	ok = _processS1Folder(source)
	if ok == -1:
		print("Could not process", source)
		exit()
	
	# if -g, all resulting files are aggregated
	if join:
		generateAgregate(source)
	
else:
	print(source, "is neither an existing file or folder")
	


	
