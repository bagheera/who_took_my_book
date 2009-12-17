# hardcode created date to 10-May-2009 for all books without a  created date

from google.appengine.ext import db
from wtmb import Book
import datetime

print 'starting'
all_books = db.GqlQuery("SELECT __key__ from Book LIMIT 1000").fetch(1000)
print 'all books count = ' + str(len(all_books))
books_with_cdate = db.GqlQuery("SELECT __key__ from Book WHERE created_date > DATE(2009, 5, 14) LIMIT 1000").fetch(1000)
print 'new books count = ' + str(len(books_with_cdate))
for key in books_with_cdate:
    all_books.remove(key)
print 'old books count = ' + str(len(all_books))
for key in all_books:
    oldBook = Book.get(key)
    print "<br>updating date for " + oldBook.title
    oldBook.created_date = datetime.datetime(2009, 5, 10)
    oldBook.put()
