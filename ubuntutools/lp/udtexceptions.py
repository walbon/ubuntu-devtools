class PackageNotFoundException(BaseException):
	""" Thrown when a package is not found """
	pass
		
class SeriesNotFoundException(BaseException):
	""" Thrown when a distroseries is not found """
	pass

class PocketDoesNotExistException(BaseException):
	""" Thrown when a invalid pocket is passed """
	pass

class ArchiveNotFoundException(BaseException):
	""" Thrown when an archive for a distibution is not found """
	pass

class AlreadyLoggedInError(Exception):
    '''Raised when a second login is attempted.'''
    pass
