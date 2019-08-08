

# folders and filenames involved in corpus construction
MODELS_FOLDER = "../models"
if not os.path.exists(MODELS_FOLDER):
	os.makedirs(MODELS_FOLDER)

KORPUS_FOLDER = "../KORPUS"

LEE_D2V_MODEL = MODELS_FOLDER + "/model_d2v_lee.model"

OWN_D2V_MODEL = MODELS_FOLDER + "/model_d2v_own.model"

TRAINING_TEXTS_FOLDER = KORPUS_FOLDER + '/original_texts'

#DEFAULT_TRAINING_TEXTS = "historical_modify.txt"
DEFAULT_TRAINING_TEXTS = "originales.s.w"




URL_Stanford = "http://localhost:9000"

# class to manage word identification with the Stanfors tool
class StanfordBroker:
	# to init a broker to the Stanford service, that must be running in this host
	def __init__(self):
		self.nlpStanfordBroker =  StanfordCoreNLP(URL_Stanford)  
		
	# to request identification of words in a sentence
	def identifyWords (self, sentence):		
		# pasamos la frase por el stanford para saber qué tipo de palabras componen la frase  (res tiene el formato que se puede ver en la sec 6.1)
		res = self.nlpStanfordBroker.annotate(sentence, properties={'annotators': 'tokenize,ssplit,pos,lemma', 'outputFormat': 'json'})
		
		return res["sentences"][0]["tokens"]
	
	
	
	