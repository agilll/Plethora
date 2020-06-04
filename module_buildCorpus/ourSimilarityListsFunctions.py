from math import *
from decimal import Decimal

def printl(message):
	try:
		from studySims import ddgg
		if ddgg == True:
			print(message)
	except Exception:
		pass

# Math similarities functions over lists
class ourSimilarityListsFunctions():


	# return cosine similarity between two lists of numbers
	def oCosineSimilarity (self,x,y):
		numerator = sum(a*b for a,b in zip(x,y))
		denominator = self.square_rooted(x)*self.square_rooted(y)
		return round(numerator/float(denominator),3)

	# returns the jaccard similarity between two lists of general elements (may be word tokens)
	def oJaccardSimilarity (self,x,y):
		intersection_cardinality = len(set.intersection(set(x), set(y)))
		union_cardinality = len(set.union(set(x), set(y)))

		# printl("len x = "+str(len(x)))
		# printl("len y = "+str(len(y)))
		# printl("len intersection = "+str(intersection_cardinality))
		# printl(set.intersection(set(x), set(y)))
		# printl("len union = "+str(union_cardinality))

		return intersection_cardinality/float(union_cardinality)

	# return euclidean distance between two lists of numbers
	def oEuclideanDistance (self,x,y):
		return sqrt(sum(pow(a-b,2) for a, b in zip(x, y)))


	# return manhattan distance between two lists of numbers
	def oManhattanDistance (self,x,y):
		return sum(abs(a-b) for a,b in zip(x,y))


	# return minkowski distance between two lists of numbers
	def oMinkowskiDistance (self,x,y,p_value):
		return self.nth_root(sum(pow(abs(a-b),p_value) for a,b in zip(x, y)), p_value)


	# returns the n_root of an value
	def nth_root (self,value, n_root):
		root_value = 1/float(n_root)
		return round (Decimal(value) ** Decimal(root_value),3)


	# return 3 rounded square rooted value for a list
	def square_rooted (self,x):
		return round(sqrt(sum([a*a for a in x])),3)
