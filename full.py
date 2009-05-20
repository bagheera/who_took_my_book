from django.utils import simplejson
from google.appengine.ext import webapp
from wtmb import Book
from bookcache import *

class FullListing(webapp.RequestHandler):

    def get(self):
        self.response.headers['content-type'] = "application/json"
        data = {}
        me = AppUser.me()
        data['user'] = me.to_hash()
        data['mybooks'] = self.books_owned_by(me)
        data['borrowedBooks'] = self.books_borrowed_by(AppUser.me())
#        'Keys only queries do not support IN or != filters.'
#        others_books = map(CachedBook.get, Book.others_books())
        others_books = []
        for user in AppUser.others():
            books = self.books_owned_by(user)
            if not len(books) == 0:
                others_books.extend(books)
        data['others'] = others_books
        self.response.out.write(simplejson.dumps(data))

    def books_owned_by(self, appUser):
        books_owned_ids = CacheBookIdsOwned.get(appUser.key())
        return self.books_by_title(books_owned_ids) if books_owned_ids else []

    def books_borrowed_by(self, appUser):
        books_owned_ids = CacheBookIdsBorrowed.get(appUser.key())
        return self.books_by_title(books_owned_ids) if books_owned_ids else []

    def books_by_title(self, books_owned):
        book_hashes = map(CachedBook.get, books_owned)
        book_hashes.sort(lambda x, y: cmp(y['title'], x['title']))
        return book_hashes

