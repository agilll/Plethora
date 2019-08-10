from math import *
from decimal import Decimal

# Math similarities function
class mathSimilarity():

	# return cosine similarity between two lists
	def cosine_similarity(self,x,y):
		numerator = sum(a*b for a,b in zip(x,y))
		denominator = self.square_rooted(x)*self.square_rooted(y)
		return round(numerator/float(denominator),3)

	# returns the jaccard similarity between two lists
	def jaccard_similarity(self,x,y):
		intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
		union_cardinality = len(set.union(*[set(x), set(y)]))
		return intersection_cardinality/float(union_cardinality)

	# return euclidean distance between two lists
	def euclidean_distance(self,x,y):
		return sqrt(sum(pow(a-b,2) for a, b in zip(x, y)))


	# return manhattan distance between two lists
	def manhattan_distance(self,x,y):
		return sum(abs(a-b) for a,b in zip(x,y))


	# return minkowski distance between two lists
	def minkowski_distance(self,x,y,p_value):
		return self.nth_root(sum(pow(abs(a-b),p_value) for a,b in zip(x, y)), p_value)


	# returns the n_root of an value
	def nth_root(self,value, n_root):
		root_value = 1/float(n_root)
		return round (Decimal(value) ** Decimal(root_value),3)


	# return 3 rounded square rooted value
	def square_rooted(self,x):
		return round(sqrt(sum([a*a for a in x])),3)
