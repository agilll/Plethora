# script to test function processS4List in S4_tokenize.py

# input: a list of .w files 
# output: foreach .w file a .t file will be created



import os
import sys

from S4_tokenize import processS4List as _processS4List

# parameter checking

# at least, one param
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" folder")
	exit(-1)

# if only one param, cannot start by '-'
if len(sys.argv) == 2:
	if sys.argv[1][0] == "-":
		print("Use: "+sys.argv[0]+" folder")
		exit(-1)
	else:
		source = sys.argv[1]  # this is the file|folder with the source data

# error if more than one param
else:
	print("Use: "+sys.argv[0]+" folder")
	exit(-1)
	
	
# start processing
	
print("Processing list...")
_processS4List(["/Users/agil/GitHub/Plethora/CORPUS/files_s_p_w/d01.txt.s.w", "/Users/agil/GitHub/Plethora/CORPUS/files_s_p_w/d02.txt.s.w"], source)



	


	
