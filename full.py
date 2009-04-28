from google.appengine.ext import webapp
from wtmb import Book

class FullListing(webapp.RequestHandler):
    def get(self):
        self.response.headers['content-type'] = "application/json"
        self.response.out.write('{ mybooks: [')
        #streaming one by one might be better than fetch all and map
        self.response.out.write(",".join(map(Book.to_json, Book.my_books().fetch(1000))))
        self.response.out.write('], borrowedBooks: [')
        self.response.out.write(",".join(map(Book.to_json, Book.borrowed_books().fetch(1000))))
        self.response.out.write('], others: [')
        self.response.out.write(",".join(map(Book.to_json, Book.others_books().fetch(1000))))
        self.response.out.write(']}')
