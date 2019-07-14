from sarac.core import parser

MAX_FILE_SIZE = 4096

file = open('testfile', 'r')

print parser.parse(file.read())