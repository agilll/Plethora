# script to test function processS2List in S2_BuildDbpediaInfoFromTexts.py

# input: a list of .s files
# outputs: several files will be created in the same folder
#			a file with '.s.p' extension for each processed file
#			a .s.p.html file with the entities marked in green


import os
import sys

from S2_BuildDbpediaInfoFromTexts import processS2List as _processS2List

# parameter checking

# one parameter is required  
if len(sys.argv) > 1:
	print("Use: python3 "+sys.argv[0])
	exit(-1)
	
	
# start processing
	
print("Processing list...")
_processS2List(["/Users/agil/GitHub/Plethora/CORPUS/files_s_p_w/d01.txt.s", "/Users/agil/GitHub/Plethora/CORPUS/files_s_p_w/d02.txt.s"])



	


	
