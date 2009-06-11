class PackageNotFoundException(BaseException):
	""" Thrown when a package is not found """
	pass
		
class SeriesNotFoundException(BaseException):
	""" Thrown when a distroseries is not found """
	pass

class PocketDoesNotExist(BaseException):
	""" Thrown when a invalid pocket is passed """
	pass
