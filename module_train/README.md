Subproject  to train Word2Vec and Doc2Vec networks

buildD2VLeeModel.py - To train a Doc2Vec model with Lee corpus

buildD2VOwnModel-txt.py - To train a Doc2Vec model with our own .txt files

buildD2VOwnModel-t.py - To train a Doc2Vec model with our own .t files (the txt files have been processed to remove stopwords, convert to lemmas... and tokenized to list of sentences, each one being a list of words). It is a simple caller, it uses D2V_BuildOwnModel_t.py for this task


trainW2VModel.py - To train a Word2Vec model with .t files

It requires ../CORPUS/files_t with the training files
It saves the models in current folder

python3 trainW2VModel.py folder
