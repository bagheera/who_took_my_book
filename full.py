from google.appengine.ext import webapp
from wtmb import Book

class FullListing(webapp.RequestHandler):
    def get(self):
        self.response.headers['content-type'] = "text/xml"
        for book in Book.all().fetch(1000):
            self.response.out.write(book.to_xml())