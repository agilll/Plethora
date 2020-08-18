# training with 100 epochs, min_count=5, and .t files (preprocessed .txt files)
# a .t file contains a binary structure (pickle saved): a list of lists of words (already lemmas). That is, tokenization has already been done

from aux_train import TRAINING_T_FOLDER as _TRAINING_T_FOLDER, OWN_D2V_MODEL as _OWN_D2V_MODEL

from D2V_BuildOwnModel_t import buildD2VModelFrom_T_Folder as _buildD2VModelFrom_T_Folder

# variables init

model_filename = _OWN_D2V_MODEL + "-t.model"

vector_size = 20	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 8	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses

# seed = 1 # Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)

min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 1	# Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs = 100	# epochs (int, optional) – Number of iterations (epochs) over the corpus


# Build a doc2vec model trained with files in _TRAINING_T_FOLDER folder
r =_buildD2VModelFrom_T_Folder(_TRAINING_T_FOLDER, model_filename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

if (r != 0):
	print("Training failed!")
