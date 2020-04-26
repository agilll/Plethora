# script to test function processList in S1_AddSuffixToTexts.py

# input: a folder, the base corpus folder for output files
# outputs:	for each processed file, several files will be created 
#			a file with the original name and the suffix '.s', for every processed file
#			a .s.html' file with the changes in green, for every processed file (just to easily read changes)
#           a .s.nr with report about studied changes finally not done (for debugging) 
#           a .s.nr.html with HTML report about studied changes finally not done (for debugging) 

#		In case of the '-g' modifier a new file 'folder/folder.s' will be created aggregating all the created '.s' files in folder/files_s_p_w.

import os
import sys

from S1_AddSuffixToTexts import processS1List as _processS1List


# variable to control if aggregation must be created     
join = False

# parameter checking

# one parameter is required  
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" [-g] folder")
	exit(-1)

# one parameter, it is the folder
if len(sys.argv) == 2:
	source = sys.argv[1]
	
# two parameters, the first one must be '-g', the second one is the file|folder
elif len(sys.argv) == 3:
	if sys.argv[1] == "-g":
		join = True
		source = sys.argv[2]
	else:
		print("Use: "+sys.argv[0]+" [-g] folder")
		exit(-1)

# more than two parameters is not permitted
else:
	print("Use: "+sys.argv[0]+" [-g] folder")
	exit(-1)

	
	
# start processing
	
# source is a folder. It will be the base CORPUS folder for output files. It will be created in processList if does not exist
	
print("Processing list...")
_processS1List(source, ["/Users/agil/Google Drive/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Eudamidas_I.txt", "/Users/agil/Google Drive/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Pleistarchus.txt"])


# if -g, all resulting files are aggregated
if join:
	generateAgregate(source)
	

	


	
