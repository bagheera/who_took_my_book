from google.appengine.ext import webapp
from wtmb import Book
from bookcache import *

class FullListing(webapp.RequestHandler):
    def get(self):
        self.response.headers['content-type'] = "application/json"
        self.response.out.write('{ ')
        books = self.books_owned_by(AppUser.me())
        exist = False
        if not len(books) == 0:
            self.response.out.write('mybooks: [')
            self.response.out.write(",".join(books))
            self.response.out.write(']')
            exist = True
        books = self.books_borrowed_by(AppUser.me())
        if not len(books) == 0:
            self.response.out.write(', borrowedBooks: [') if exist else self.response.out.write('borrowedBooks: [')
            exist = True
            self.response.out.write(",".join(books))
            self.response.out.write(']')
        self.response.out.write(', others: [') if exist else self.response.out.write('others: [')
        others_books = []
        for user in AppUser.others():
            books = self.books_owned_by(user)
            if not len(books) == 0:
                others_books.extend(books)
        self.response.out.write(",".join(others_books))
        self.response.out.write(']}')

    def books_owned_by(self, appUser):
        books_owned = CacheBookIdsOwned.get(str(appUser.key()))
        return map(CachedBook.get, books_owned) if books_owned else []

    def books_borrowed_by(self, appUser):
        books = CacheBookIdsBorrowed.get(str(appUser.key()))
        logging.info("bb_by " + str(books))
        return map(CachedBook.get, books) if books else []
